"""Urban API models are defined here."""

import json
from datetime import datetime, timezone
from typing import Any, Literal

import shapely
import shapely.geometry as geom
from pydantic import BaseModel, Field

_BaseGeomTypes = (
    geom.Point | geom.MultiPoint | geom.Polygon | geom.MultiPolygon | geom.LineString | geom.MultiLineString
)


class Geometry(BaseModel):
    """
    Geometry representation for GeoJSON model appliable for points, polygons, multipolygons and linestrings.
    """

    type: Literal["Point", "MultiPoint", "Polygon", "MultiPolygon", "LineString", "MultiLineString"] = Field(
        examples=["Polygon"]
    )
    coordinates: list[Any] = Field(
        description="list[float] for Point,\n" "list[list[list[float]]] for Polygon",
        examples=[
            [
                [
                    [30.22, 59.86],
                    [30.22, 59.85],
                    [30.25, 59.85],
                    [30.25, 59.86],
                    [30.22, 59.86],
                ]
            ]
        ],
    )
    _shapely_geom: _BaseGeomTypes | None = None

    def as_shapely_geometry(self) -> _BaseGeomTypes:
        """
        Return Shapely geometry object from the parsed geometry.
        """
        if self._shapely_geom is None:
            self._shapely_geom = shapely.from_geojson(json.dumps({"type": self.type, "coordinates": self.coordinates}))
        return self._shapely_geom

    @classmethod
    def from_shapely_geometry(cls, geometry: _BaseGeomTypes | None) -> "Geometry":
        """
        Construct Geometry model from shapely geometry.
        """
        if geometry is None:
            return None
        return cls(**geom.mapping(geometry))


class Point(Geometry):
    """
    Geometry representation for GeoJSON model appliable for points only.
    """

    type: Literal["Point"] = "Point"
    coordinates: list[float] = Field(description="list[float]", examples=[[30.22, 59.86]])
    _shapely_geom: _BaseGeomTypes | None = None


class ShortTerritory(BaseModel):
    """Basic territory model to encapsulate in other models."""

    id: int
    name: str


class ShortScenario(BaseModel):
    """Basic scenario model to encapsulate in other models."""

    id: int
    name: str


class ShortProject(BaseModel):
    """Basic project model to encapsulate in other models."""

    project_id: int = Field(..., description="project identifier", examples=[1])
    user_id: str = Field(..., description="project creator identifier", examples=["admin@test.ru"])
    name: str = Field(..., description="project name", examples=["--"])
    region: ShortTerritory


class ShortProjectWithScenario(BaseModel):
    """Basic project with scenario model to encapsulate in other models."""

    project_id: int = Field(..., description="project identifier", examples=[1])
    user_id: str = Field(..., description="project creator identifier", examples=["admin@test.ru"])
    name: str = Field(..., description="project name", examples=["--"])
    region: ShortTerritory
    base_scenario: ShortScenario


class FunctionalZoneTypeBasic(BaseModel):
    """Basic functional zone type model to encapsulate in other models."""

    id: int
    name: str
    nickname: str
    description: str


class Scenario(BaseModel):
    """Scenario with all its attributes."""

    scenario_id: int = Field(..., description="scenario identifier", examples=[1])
    parent_scenario: ShortScenario | None
    project: ShortProject
    functional_zone_type: FunctionalZoneTypeBasic | None
    name: str = Field(..., description="name of the scenario", examples=["--"])
    is_based: bool = Field(..., description="boolean parameter to determine base scenario")
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="scenario additional properties",
        examples=[{"attribute_name": "attribute_value"}],
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="the time when the scenario was created"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="the time when the scenario was last updated"
    )


class Project(BaseModel):
    """Project with all its attributes."""

    project_id: int = Field(..., description="project identifier", examples=[1])
    user_id: str = Field(..., description="project creator identifier", examples=["admin@test.ru"])
    name: str = Field(..., description="project name", examples=["--"])
    territory: ShortTerritory
    base_scenario: ShortScenario | None
    description: str | None = Field(..., description="project description", examples=["--"])
    public: bool = Field(..., description="project publicity", examples=[True])
    is_regional: bool = Field(..., description="boolean parameter for regional projects", examples=[False])
    is_city: bool = Field(..., description="boolean parameter to determine city project")
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="project's additional properties",
        examples=[{"additional_attribute_name": "additional_attribute_value"}],
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="project created at")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="project updated at")


class ProjectTerritory(BaseModel):
    """Project territory with all its attributes."""

    project_territory_id: int = Field(..., description="project territory id", examples=[1])
    project: ShortProjectWithScenario
    geometry: Geometry
    centre_point: Point | None = None
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="project territory additional properties",
        examples=[{"attribute_name": "attribute_value"}],
    )


class ProjectCadastrePut(BaseModel):
    """Project cadastres schema for PUT request."""

    geometry: Geometry
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional cadastre properties (JSONB)",
    )
    area: float | None = Field(None, examples=[1250.5])
    cad_num: str | None = Field(None, examples=["77:01:0004012:345"])
    cost_value: float | None = Field(None, examples=[1500000.0])
    land_record_area: float | None = Field(None, examples=[1200.0])
    land_record_category_type: str | None = Field(None, examples=["Земли населённых пунктов"])
    ownership_type: str | None = Field(None, examples=["Собственность"])
    permitted_use_established_by_document: str | None = Field(
        None,
        examples=["Для размещения объектов жилой застройки"],
    )
    quarter_cad_number: str | None = Field(None, examples=["77:01:0004012"])
    readable_address: str | None = Field(
        None,
        description="Human-readable address",
        examples=["г. Москва, ул. Тверская, д. 1"],
    )
    specified_area: float | None = Field(None, examples=[1230.0])
    status: str | None = Field(None, examples=["Учтён"])
    zone_pzz: str | None = Field(None, examples=["Ж-1"])
    possible_pzz_vri: str | None = Field(None, examples=["Жилая застройка"])
    possible_vri_list: str | None = Field(
        None,
        description="Possible permitted use list (raw text)",
    )
    similarity_score: float | None = Field(
        None,
        description="Similarity score between cadastre object and project territory",
        examples=[0.92],
    )
