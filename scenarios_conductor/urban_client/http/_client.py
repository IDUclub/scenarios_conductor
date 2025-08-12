"""Urban API HTTP Client is defined here."""

import asyncio
from collections.abc import Callable
from datetime import date
from functools import wraps
from typing import Literal

import structlog.stdlib
from aiohttp import ClientConnectionError, ClientResponse, ClientSession, ClientTimeout

from scenarios_conductor.urban_client._abstract import UrbanClient
from scenarios_conductor.urban_client.exceptions import APIConnectionError, APITimeoutError
from scenarios_conductor.urban_client.http.exceptions import (
    BadRequest,
    ConflictAlreadyExists,
    EntityNotFound,
    InvalidStatusCode,
)
from scenarios_conductor.urban_client.http.models import Paginated
from scenarios_conductor.urban_client.models import Project, Scenario


def _handle_exceptions(func: Callable) -> Callable:
    """Decorator to handle exceptions."""

    @wraps(func)
    async def _wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ClientConnectionError as exc:
            raise APIConnectionError("Error on connection to Urban API") from exc
        except asyncio.exceptions.TimeoutError as exc:
            raise APITimeoutError("Timeout expired on Urban API request") from exc

    return _wrapper


class HTTPUrbanClient(UrbanClient):
    """Urban API client that uses HTTP/HTTPS as transport."""

    def __init__(
        self,
        host: str,
        api_token: str,
        *,
        ping_timeout_seconds: float = 2.0,
        operation_timeout_seconds: float = 60.0,
        logger: structlog.stdlib.BoundLogger = ...,
    ):
        if logger is ...:
            logger = structlog.get_logger()
        if not host.startswith("http"):
            logger.warning("http/https schema is not set, defaulting to http")
            host = f"http://{host.rstrip('/')}/"

        self._host = host
        self._api_token = api_token
        self._logger = logger.bind(host=self._host)
        self._ping_timeout = ping_timeout_seconds
        self._operation_timeout = operation_timeout_seconds

        self._session: ClientSession | None = None

    def get_headers(self) -> dict[str, str]:
        """Return request headers."""
        return {"Authorization": f"Bearer {self._api_token}"}

    async def __aenter__(self):
        return self.start()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def start(self):
        self._session = ClientSession(base_url=self._host, timeout=ClientTimeout(self._operation_timeout))
        return self

    async def close(self):
        if self._session:
            await self._session.close()
            self._session = None

    def _get_session(self) -> ClientSession:
        """Get client session."""
        if self._session is None or self._session.closed:
            self._session = ClientSession(base_url=self._host, timeout=ClientTimeout(self._operation_timeout))
        return self._session

    async def _request(self, method: str, path: str, **kwargs) -> ClientResponse:
        session = self._get_session()
        kwargs.setdefault("headers", self.get_headers())
        resp: ClientResponse = await session.request(method, path, **kwargs)
        if resp.status in (200, 201):
            return resp
        if resp.status == 400:
            raise BadRequest(f"{method} {path} returned BAD REQUEST: {await resp.text()}")
        if resp.status == 404:
            raise EntityNotFound(f"{method} {path} returned NOT FOUND: {await resp.text()}")
        if resp.status == 409:
            raise ConflictAlreadyExists(f"{method} {path} returned CONFLICT: {await resp.text()}")
        await self._logger.aerror(f"request failed: {method} {path}", status=resp.status, text=await resp.text())
        raise InvalidStatusCode(f"{method} {path} returned unexpected status: {resp.status}")

    async def is_alive(self) -> bool:
        try:
            session = self._get_session()
            resp = await session.get("health_check/ping", timeout=ClientTimeout(self._ping_timeout))
            if resp.status == 200 and (await resp.json()) == {"message": "Pong!"}:
                return True
            await self._logger.awarning("error on ping", resp_code=resp.status, resp_text=await resp.text())
        except ClientConnectionError as exc:
            await self._logger.awarning("error on ping", error=repr(exc))
        except asyncio.exceptions.TimeoutError:
            await self._logger.awarning("timeout on ping")
        return False

    @_handle_exceptions
    async def get_version(self) -> str:
        resp = await self._request("GET", "api/openapi")
        return (await resp.json())["info"]["version"]

    @_handle_exceptions
    async def get_project_by_id(self, project_id: int) -> Project:
        resp = await self._request("GET", f"api/v1/projects/{project_id}")
        return Project.model_validate_json(await resp.text()) if resp else None

    @_handle_exceptions
    async def get_scenario_by_id(self, scenario_id: int) -> Scenario:
        resp = await self._request("GET", f"api/v1/scenarios/{scenario_id}")
        return Scenario.model_validate_json(await resp.text()) if resp else None

    @_handle_exceptions
    async def get_scenarios(
        self,
        parent_id: int | None = None,
        project_id: int | None = None,
        territory_id: int | None = None,
        is_based: Literal["true", "false"] = "false",
        only_own: Literal["true", "false"] = "false",
    ) -> list[Scenario]:
        params = {"is_based": is_based, "only_own": only_own}
        if parent_id is not None:
            params["parent_id"] = parent_id
        if project_id is not None:
            params["project_id"] = project_id
        if territory_id is not None:
            params["territory_id"] = territory_id

        resp = await self._request("GET", "api/v1/scenarios", params=params)
        return [Scenario.model_validate(entry) for entry in await resp.json()] if resp else None

    @_handle_exceptions
    async def get_projects(
        self,
        only_own: Literal["true", "false"] = "false",
        is_regional: Literal["true", "false"] = "false",
        project_type: Literal["common", "city"] | None = None,
        territory_id: int | None = None,
        name: str | None = None,
        created_at: date | None = None,
        page_size: int = 100,
    ) -> list[Project]:
        params = {"is_regional": is_regional, "only_own": only_own, "page_size": page_size}
        if project_type is not None:
            params["project_type"] = project_type
        if territory_id is not None:
            params["territory_id"] = territory_id
        if name is not None:
            params["name"] = name
        if created_at is not None:
            params["created_at"] = created_at

        session = self._get_session()
        resp = await self._request("GET", "api/v1/projects", params=params)
        result = Paginated[Project].model_validate_json(await resp.text()) if resp else None
        return await result.get_all_pages(session) if result else None

    @_handle_exceptions
    async def create_base_scenario(self, project_id: int, scenario_id: int) -> Scenario:
        resp = await self._request("POST", f"api/v1/projects/{project_id}/base_scenario/{scenario_id}")
        return Scenario.model_validate_json(await resp.text()) if resp else None
