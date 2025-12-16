"""This module contains the ProjectCadastreService class, which is responsible for
handling cadastre data processing for newly created projects.
"""
import math
import pickle
from collections.abc import Iterable
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
import structlog
from otteroad.models import ProjectCreated

from scenarios_conductor.urban_client import UrbanClient
from scenarios_conductor.urban_client.http.exceptions import BadRequest, EntityNotFound
from scenarios_conductor.urban_client.models import Geometry, ProjectCadastrePut, ProjectTerritory

CADASTRE_COLUMN_MAP: dict[str, str] = {
    # ProjectCadastrePut field        # GDF column
    "area": "options_area",
    "cad_num": "options_cad_num",
    "cost_value": "options_cost_value",
    "land_record_area": "options_land_record_area",
    "land_record_category_type": "options_land_record_category_type",
    "ownership_type": "options_ownership_type",
    "permitted_use_established_by_document": "options_permitted_use_established_by_document",
    "quarter_cad_number": "options_quarter_cad_number",
    "readable_address": "options_readable_address",
    "specified_area": "options_specified_area",
    "status": "status",
    "zone_pzz": "zone_pzz",
    "possible_pzz_vri": "possible_vri_pzz",
    "possible_vri_list": "possible_vri_list",
    "similarity_score": "similarity_score",
}


class ProjectCadastreService:
    """Service for handling cadastre data processing for projects."""

    def __init__(
        self,
        urban_client: UrbanClient,
        cadastre_file_path: str,
        logger: structlog.stdlib.BoundLogger,
    ):
        self._urban_client = urban_client
        self._cadastre_file_path = cadastre_file_path
        self._cadastre_gdf: gpd.GeoDataFrame | None = None
        self._logger = logger

        self._load_cadastre()

    # -------------------------
    # Cadastre loading
    # -------------------------

    @staticmethod
    def _expand_dict_column(
        gdf: gpd.GeoDataFrame,
        column: str,
        prefix: str,
    ) -> gpd.GeoDataFrame:
        """
        Expand dict column into separate columns with prefix.

        Example:
            options = {"a": 1, "b": 2}
            -> options_a, options_b
        """
        if column not in gdf.columns:
            return gdf

        # replace non-dict with empty dict
        series = gdf[column].apply(lambda x: x if isinstance(x, dict) else {})

        expanded = pd.json_normalize(series).add_prefix(f"{prefix}_")

        # keep index alignment
        expanded.index = gdf.index

        # drop original column and concat
        gdf = pd.concat(
            [gdf.drop(columns=[column]), expanded],
            axis=1,
        )

        return gdf

    def _load_cadastre(self):
        """Load cadastre GeoDataFrame from pickle file and reproject to EPSG:4326."""

        if self._cadastre_gdf is not None:
            return

        with open(self._cadastre_file_path, "rb") as f:
            data = pickle.load(f)

        if not isinstance(data, gpd.GeoDataFrame):
            raise TypeError(f"Cadastre file must contain GeoDataFrame, got {type(data)}")

        if data.crs is None:
            raise ValueError("Cadastre GeoDataFrame has no CRS defined")

        original_crs = data.crs

        if original_crs.to_epsg() != 4326:
            data = data.to_crs(epsg=4326)

        data = self._expand_dict_column(data, "options", "options")
        data = self._expand_dict_column(data, "system_info", "system")

        self._cadastre_gdf = data

        self._logger.info(
            "Cadastre loaded",
            features=len(data),
            crs=str(data.crs),
        )

    # -------------------------
    # Spatial logic
    # -------------------------

    def _clip_to_territory(
        self,
        territory: ProjectTerritory,
    ) -> Iterable[ProjectCadastrePut]:
        """
        Clip cadastre objects to project territory and convert them
        to ProjectCadastrePut models.
        """

        territory_geom = territory.geometry.as_shapely_geometry()

        if self._cadastre_gdf.crs is None:
            self._logger.awarning(
                "Cadastre CRS is not defined, assuming same CRS",
                project_id=territory.project.project_id,
            )

        clipped = gpd.clip(
            self._cadastre_gdf,
            territory_geom,
            keep_geom_type=True,
        )

        self._logger.info(
            "Cadastre clipped to territory",
            project_id=territory.project.project_id,
            matched=len(clipped),
        )

        for _, row in clipped.iterrows():
            yield self._row_to_project_cadastre(row)

    @staticmethod
    def _normalize_value(val):
        """Normalize values to JSON- and API-safe primitives."""

        if val is None:
            return None

        # pandas / numpy NaN / NA
        try:
            if pd.isna(val):
                return None
        except Exception:
            pass

        # float NaN (на всякий случай)
        if isinstance(val, float) and math.isnan(val):
            return None

        # numpy scalar -> python scalar
        if isinstance(val, np.generic):
            val = val.item()
            if isinstance(val, float) and math.isnan(val):
                return None

        # numpy array
        if isinstance(val, np.ndarray):
            if val.size == 0 or np.any(pd.isna(val)):
                return None
            val = val.tolist()

        # list / tuple -> string
        if isinstance(val, (list, tuple)):
            if not val:
                return None
            return "; ".join(str(v) for v in val if v is not None)

        return val

    def _row_to_project_cadastre(self, row: pd.Series) -> ProjectCadastrePut:
        """Convert GeoDataFrame row to ProjectCadastrePut."""

        # --- geometry ---
        geom = row.get("geometry")
        geometry = Geometry.from_shapely_geometry(geom) if geom is not None and not geom.is_empty else None

        # --- mapped fields ---
        kwargs: dict[str, Any] = {}
        for model_field, gdf_column in CADASTRE_COLUMN_MAP.items():
            raw = row.get(gdf_column)
            val = self._normalize_value(raw)
            if val is not None:
                kwargs[model_field] = val

        # --- base properties ---
        used_columns = {"geometry"} | set(CADASTRE_COLUMN_MAP.values())

        properties = {
            col: self._normalize_value(val)
            for col, val in row.items()
            if col not in used_columns and self._normalize_value(val) is not None
        }

        return ProjectCadastrePut(
            geometry=geometry,
            properties=properties,
            **kwargs,
        )

    # -------------------------
    # Event handler
    # -------------------------

    async def handle_project_created(self, event: ProjectCreated):
        """Handles the ProjectCreated event for cadastre processing."""
        try:
            territory = await self._urban_client.get_project_territory_by_project_id(event.project_id)

            if not territory or not territory.geometry:
                await self._logger.awarning(
                    "Territory not found or has no geometry",
                    project_id=event.project_id,
                )
                return

            cadastres = list(self._clip_to_territory(territory))

            if not cadastres:
                await self._logger.ainfo(
                    "No cadastre features found within territory",
                    project_id=event.project_id,
                )
                return

            await self._urban_client.put_project_cadastres(
                cadastres=cadastres,
                project_id=event.project_id,
            )

            await self._logger.ainfo(
                "Cadastre data uploaded to project",
                project_id=event.project_id,
                cadastre_count=len(cadastres),
            )

        except EntityNotFound:
            await self._logger.awarning(
                "Project or territory not found",
                project_id=event.project_id,
            )
        except BadRequest as exc:
            await self._logger.aerror(
                "Failed to upload cadastre data",
                project_id=event.project_id,
                error=str(exc),
            )
        except Exception:
            await self._logger.aexception(
                "Unexpected error while processing cadastre data",
                project_id=event.project_id,
            )
            raise
