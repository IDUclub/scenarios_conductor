"""Regression checks for disk-backed cadastre and download cleanup."""

import asyncio
import io
import json
import pickle
import sqlite3
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import geopandas as gpd
import pytest
from shapely.geometry import box

from scenarios_conductor.config import AppConfig, CadastreConfig
from scenarios_conductor.services.cadastre import ProjectCadastreService
from scenarios_conductor.utils.minio import download_from_minio


def test_geopackage_matches_pickle_and_reads_only_candidates(tmp_path):
    source = tmp_path / "cadastre.pickle"
    destination = tmp_path / "cadastre.gpkg"
    data = gpd.GeoDataFrame(
        {
            "options": [{"cad_num": "one", "area": 1}, {"cad_num": "two"}, {}],
            "system_info": [{"source": "sample"}, {}, {}],
            "possible_vri_list": [["a", "b"], [], []],
            "extra": [None, "other", "outside"],
        },
        geometry=[box(0, 0, 2, 2), box(2, 2, 3, 3), box(20, 20, 21, 21)],
        crs=4326,
        index=[3, 7, 9],
    ).to_crs(3857)
    with source.open("wb") as stream:
        pickle.dump(data, stream)
    attributes = [
        {"options_cad_num": "one", "options_area": 1, "system_source": "sample", "possible_vri_list": "a; b"},
        {"options_cad_num": "two", "extra": "other"},
        {"extra": "outside"},
    ]
    gpd.GeoDataFrame(
        {"attributes_json": [json.dumps(row) for row in attributes]},
        geometry=data.to_crs(4326).geometry.reset_index(drop=True),
        crs=4326,
    ).to_file(destination, layer="cadastre", driver="GPKG", engine="pyogrio", SPATIAL_INDEX="YES")
    with sqlite3.connect(destination) as connection:
        assert connection.execute("SELECT name FROM sqlite_master WHERE name LIKE 'rtree_%'").fetchall()
    logger = Mock()
    legacy = ProjectCadastreService(Mock(), str(source), logger)
    with patch("scenarios_conductor.services.cadastre.gpd.read_file", wraps=gpd.read_file) as reader:
        disk = ProjectCadastreService(Mock(), str(destination), logger)
        reader.assert_not_called()
        assert disk._cadastre_gdf is None
        territory = SimpleNamespace(
            geometry=SimpleNamespace(as_shapely_geometry=lambda: box(0.5, 0.5, 2.5, 2.5)),
            project=SimpleNamespace(project_id=1),
        )
        expected = [item.model_dump() for item in legacy._clip_to_territory(territory)]
        actual = [item.model_dump() for item in disk._clip_to_territory(territory)]
        assert actual == expected
        assert len(actual) == 2
        assert reader.call_args.kwargs["bbox"] == (0.5, 0.5, 2.5, 2.5)


@pytest.mark.parametrize("failure", [None, OSError("interrupted"), KeyboardInterrupt()])
def test_download_streaming_and_cleanup(tmp_path, failure):
    config = SimpleNamespace(url="http://minio", bucket="test", access_key="key", secret_key="secret")
    response = Mock()
    response.read.side_effect = [b"payload", failure] if failure is not None else [b"payload", b""]
    with patch("scenarios_conductor.utils.minio.Minio") as client, patch("tempfile.tempdir", str(tmp_path)):
        client.return_value.get_object.return_value = response
        if failure is not None:
            with pytest.raises(type(failure)):
                download_from_minio(config, "cadastre.gpkg", Mock())
            assert list(tmp_path.iterdir()) == []
        else:
            result = Path(download_from_minio(config, "cadastre.gpkg", Mock()))
            assert result.read_bytes() == b"payload"
            assert list(tmp_path.iterdir()) == [result]
        response.close.assert_called_once()
        response.release_conn.assert_called_once()
        assert all(call.args == (1024 * 1024,) for call in response.read.call_args_list)


def test_download_request_failure_removes_placeholder(tmp_path):
    config = SimpleNamespace(url="http://minio", bucket="test", access_key="key", secret_key="secret")
    with patch("scenarios_conductor.utils.minio.Minio") as client, patch("tempfile.tempdir", str(tmp_path)):
        client.return_value.get_object.side_effect = OSError("offline")
        with pytest.raises(OSError):
            download_from_minio(config, "cadastre.pickle", Mock())
    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
@pytest.mark.parametrize("fail_loading", [True, False])
async def test_startup_and_shutdown_preserve_mounted_file(tmp_path, fail_loading):
    from scenarios_conductor import __main__ as app

    downloaded = tmp_path / "cadastre.gpkg"
    downloaded.write_bytes(b"placeholder")
    config = Mock()
    config.cadastre.path = str(downloaded)
    config.logging.files = []
    config.prometheus.disable = True
    client = AsyncMock()
    consumer = Mock()
    consumer.stop = AsyncMock()

    async def start():
        assert downloaded.exists()
        raise asyncio.CancelledError()

    consumer.add_worker.return_value.start = start
    with (
        patch.object(app.AppConfig, "from_file_or_default", return_value=config),
        patch.object(app, "configure_logging", return_value=AsyncMock()),
        patch.object(app.KafkaConsumerSettings, "from_custom_config"),
        patch.object(app, "KafkaConsumerService", return_value=consumer),
        patch.object(app, "make_http_client", new=AsyncMock(return_value=client)),
        patch.object(app, "ProjectCadastreService", side_effect=ValueError("invalid") if fail_loading else None),
        patch.object(app, "handlers_list", []),
    ):
        with pytest.raises(ValueError if fail_loading else asyncio.CancelledError):
            await app.main_async()
    assert downloaded.read_bytes() == b"placeholder"
    client.close.assert_awaited_once()
    consumer.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_missing_mount_fails_before_connecting(tmp_path):
    from scenarios_conductor import __main__ as app

    config = AppConfig.example()
    config.cadastre.path = str(tmp_path / "missing.gpkg")
    with (
        patch.object(app.AppConfig, "from_file_or_default", return_value=config),
        patch.object(app, "make_http_client", new_callable=AsyncMock) as client,
        patch.object(app, "KafkaConsumerService") as consumer,
    ):
        with pytest.raises(FileNotFoundError, match="Docker bind mount"):
            await app.main_async()
    client.assert_not_called()
    consumer.assert_not_called()


def test_config_roundtrip_uses_local_cadastre_without_minio():
    config = AppConfig.example()
    config.cadastre.path = "/data/another.gpkg"
    stream = io.StringIO()
    config.dump(stream)
    assert "fileserver" not in stream.getvalue()
    stream.seek(0)
    restored = AppConfig.load(stream)
    assert restored.cadastre.path == "/data/another.gpkg"
    config.update(AppConfig.example())
    assert config.cadastre.path == "/data/cadastre.gpkg"


@pytest.mark.parametrize("path", ["", " ", None, "cadastre.pickle"])
def test_config_rejects_invalid_cadastre_path(path):
    with pytest.raises(ValueError, match="cadastre.path"):
        CadastreConfig(path=path)
