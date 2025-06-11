"""Abstract protocol for Urban API client is defined here."""

import abc
from datetime import date
from typing import Literal

from scenarios_conductor.urban_client.models import Project, Scenario


class UrbanClient(abc.ABC):
    """Urban API client"""

    @abc.abstractmethod
    def start(self):
        """Start the client session."""

    @abc.abstractmethod
    async def close(self):
        """Close the client session."""

    @abc.abstractmethod
    async def _request(self, method: str, path: str, **kwargs):
        """Perform a request."""

    @abc.abstractmethod
    async def is_alive(self) -> bool:
        """Check if urban_api instance is alive."""

    @abc.abstractmethod
    async def get_version(self) -> str | None:
        """Get API version if appliable."""

    @abc.abstractmethod
    async def get_project_by_id(self, project_id: int) -> Project:
        """Get project by identifier."""

    @abc.abstractmethod
    async def get_scenario_by_id(self, scenario_id: int) -> Scenario:
        """Get scenario by identifier."""

    @abc.abstractmethod
    async def get_scenarios(
        self,
        parent_id: int | None = None,
        project_id: int | None = None,
        territory_id: int | None = None,
        is_based: bool = False,
        only_own: bool = False,
    ) -> list[Scenario]:
        """Get list of scenarios by query parameters."""

    @abc.abstractmethod
    async def get_projects(
        self,
        only_own: bool = False,
        is_regional: bool = False,
        project_type: Literal["common", "city"] | None = None,
        territory_id: int | None = None,
        name: str | None = None,
        created_at: date | None = None,
        page_size: int = 100,
    ) -> list[Project]:
        """Get list of projects by query parameters."""

    @abc.abstractmethod
    async def create_base_scenario(self, project_id: int, scenario_id: int) -> Scenario:
        """Create a new base scenario for given project from specified regional scenario."""
