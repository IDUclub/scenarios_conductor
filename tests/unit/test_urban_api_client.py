import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from aiohttp import ClientConnectionError

from scenarios_conductor.urban_client.exceptions import APIConnectionError, APITimeoutError
from scenarios_conductor.urban_client.http import HTTPUrbanClient
from scenarios_conductor.urban_client.http.exceptions import (
    BadRequest,
    ConflictAlreadyExists,
    EntityNotFound,
    InvalidStatusCode,
)


class FakeAuthClient:
    def __init__(self):
        self.entered = False
        self.closed = False
        self.headers_calls = 0

    async def __aenter__(self):
        self.entered = True
        return self

    async def get_authorization_headers(self) -> dict[str, str]:
        self.headers_calls += 1
        return {"Authorization": "Bearer token"}

    async def aclose(self):
        self.closed = True


@pytest.mark.asyncio
class TestHTTPUrbanClient:

    @pytest.fixture(autouse=True)
    def setup_client(self):
        self.auth_client = FakeAuthClient()
        self.client = HTTPUrbanClient("urban.test", self.auth_client)

    async def test_get_version_success(self):
        response_mock = AsyncMock()
        response_mock.status = 200
        response_mock.json.return_value = {"info": {"version": "1.0.0"}}

        with patch.object(self.client, "_request", return_value=response_mock):
            version = await self.client.get_version()
            assert version == "1.0.0"

    async def test_get_version_connection_error(self):
        with patch.object(self.client, "_request", side_effect=ClientConnectionError):
            with pytest.raises(APIConnectionError):
                await self.client.get_version()

    async def test_get_version_timeout(self):
        with patch.object(self.client, "_request", side_effect=asyncio.TimeoutError):
            with pytest.raises(APITimeoutError):
                await self.client.get_version()

    async def test_get_project_by_id_success(self):
        response_mock = AsyncMock()
        response_mock.status = 200
        response_mock.text.return_value = '{"id": 1, "name": "Test Project"}'

        with (
            patch.object(self.client, "_request", return_value=response_mock),
            patch(
                "scenarios_conductor.urban_client.models.Project.model_validate_json", return_value={"id": 1}
            ) as model_mock,
        ):
            project = await self.client.get_project_by_id(1)
            assert project["id"] == 1
            model_mock.assert_called_once()

    async def test_request_handles_400(self):
        response = AsyncMock()
        response.status = 400
        response.text.return_value = "bad input"

        with patch.object(
            self.client, "_get_session", return_value=AsyncMock(request=AsyncMock(return_value=response))
        ):
            with pytest.raises(BadRequest):
                await self.client._request("GET", "/some")

    async def test_request_uses_auth_client_headers(self):
        response = AsyncMock()
        response.status = 200
        session = AsyncMock(request=AsyncMock(return_value=response))

        with patch.object(self.client, "_get_session", return_value=session):
            assert await self.client._request("GET", "/some") is response

        session.request.assert_awaited_once_with("GET", "/some", headers={"Authorization": "Bearer token"})
        assert self.auth_client.headers_calls == 1

    async def test_request_handles_404(self):
        response = AsyncMock()
        response.status = 404
        response.text.return_value = "not found"

        with patch.object(
            self.client, "_get_session", return_value=AsyncMock(request=AsyncMock(return_value=response))
        ):
            with pytest.raises(EntityNotFound):
                await self.client._request("GET", "/not-found")

    async def test_request_handles_409(self):
        response = AsyncMock()
        response.status = 409
        response.text.return_value = "conflict"

        with patch.object(
            self.client, "_get_session", return_value=AsyncMock(request=AsyncMock(return_value=response))
        ):
            with pytest.raises(ConflictAlreadyExists):
                await self.client._request("GET", "/conflict")

    async def test_request_unexpected_status(self):
        response = AsyncMock()
        response.status = 500
        response.text.return_value = "internal error"

        logger_mock = AsyncMock()
        self.client._logger = logger_mock

        with patch.object(
            self.client, "_get_session", return_value=AsyncMock(request=AsyncMock(return_value=response))
        ):
            with pytest.raises(InvalidStatusCode):
                await self.client._request("GET", "/error")
            logger_mock.aerror.assert_called_once()

    async def test_is_alive_success(self):
        response_mock = AsyncMock()
        response_mock.status = 200
        response_mock.json.return_value = {"message": "Pong!"}

        with patch.object(
            self.client, "_get_session", return_value=AsyncMock(get=AsyncMock(return_value=response_mock))
        ):
            assert await self.client.is_alive() is True

    async def test_is_alive_failure(self):
        response_mock = AsyncMock()
        response_mock.status = 500
        response_mock.text.return_value = "fail"
        response_mock.json.return_value = {}

        logger_mock = AsyncMock()
        self.client._logger = logger_mock

        with patch.object(
            self.client, "_get_session", return_value=AsyncMock(get=AsyncMock(return_value=response_mock))
        ):
            assert await self.client.is_alive() is False
            logger_mock.awarning.assert_called()

    async def test_context_manager(self):
        async with self.client as instance:
            assert isinstance(instance, HTTPUrbanClient)
            assert self.client._session is not None
            assert self.auth_client.entered is True
        assert self.client._session is None
        assert self.auth_client.closed is True
