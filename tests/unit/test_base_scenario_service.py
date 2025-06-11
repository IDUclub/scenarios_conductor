from unittest.mock import AsyncMock

import pytest
import structlog
from otteroad.models import ProjectCreated, RegionalScenarioCreated

from scenarios_conductor.services import BaseScenarioService
from scenarios_conductor.urban_client.http.exceptions import BadRequest, ConflictAlreadyExists, EntityNotFound


@pytest.mark.asyncio
class TestBaseScenarioService:
    @pytest.fixture
    def mock_logger(self):
        logger = AsyncMock(spec=structlog.stdlib.BoundLogger)
        return logger

    @pytest.fixture
    def mock_client(self):
        client = AsyncMock()
        return client

    @pytest.fixture
    def service(self, mock_client, mock_logger):
        return BaseScenarioService(urban_client=mock_client, logger=mock_logger)

    async def test_handle_project_created_success(self, service, mock_client, mock_logger):
        event = ProjectCreated(project_id=1, base_scenario_id=1, territory_id=100)

        mock_project = AsyncMock()
        mock_project.user_id = 42
        mock_client.get_project_by_id.return_value = mock_project

        scenario = AsyncMock()
        scenario.project.user_id = 42
        scenario.is_based = False
        scenario.scenario_id = 10

        mock_client.get_scenarios.return_value = [scenario]
        mock_client.create_base_scenario.return_value = AsyncMock(scenario_id=99)

        await service.handle_project_created(event)

        mock_client.create_base_scenario.assert_called_once_with(project_id=1, scenario_id=10)
        mock_logger.ainfo.assert_any_call("Found matching regional scenarios", count=1, user_id=42)

    async def test_handle_project_created_project_not_found(self, service, mock_client, mock_logger):
        event = ProjectCreated(project_id=2, base_scenario_id=1, territory_id=100)
        mock_client.get_project_by_id.side_effect = EntityNotFound

        await service.handle_project_created(event)

        mock_logger.awarning.assert_called_once_with("Project not found", project_id=2)

    async def test_handle_project_created_scenarios_fetch_fail(self, service, mock_client, mock_logger):
        event = ProjectCreated(project_id=1, base_scenario_id=1, territory_id=100)
        mock_project = AsyncMock()
        mock_project.user_id = 42
        mock_client.get_project_by_id.return_value = mock_project

        mock_client.get_scenarios.side_effect = Exception("Boom")

        with pytest.raises(Exception):
            await service.handle_project_created(event)

        mock_logger.aerror.assert_called_with("Failed to fetch regional scenarios", territory_id=100)

    async def test_handle_project_created_conflict(self, service, mock_client, mock_logger):
        event = ProjectCreated(project_id=1, base_scenario_id=1, territory_id=100)

        mock_project = AsyncMock()
        mock_project.user_id = 42
        mock_client.get_project_by_id.return_value = mock_project

        scenario = AsyncMock()
        scenario.project.user_id = 42
        scenario.is_based = False
        scenario.scenario_id = 10

        mock_client.get_scenarios.return_value = [scenario]
        mock_client.create_base_scenario.side_effect = ConflictAlreadyExists

        await service.handle_project_created(event)

        mock_logger.awarning.assert_called_once()

    async def test_handle_regional_scenario_created_success(self, service, mock_client, mock_logger):
        event = RegionalScenarioCreated(scenario_id=5, territory_id=100)

        scenario = AsyncMock()
        scenario.scenario_id = 5
        scenario.project.user_id = 42
        mock_client.get_scenario_by_id.return_value = scenario

        project = AsyncMock()
        project.project_id = 1
        project.user_id = 42
        mock_client.get_projects.return_value = [project]
        mock_client.create_base_scenario.return_value = AsyncMock(scenario_id=99)

        await service.handle_regional_scenario_created(event)

        mock_client.create_base_scenario.assert_called_once_with(project_id=1, scenario_id=5)
        mock_logger.ainfo.assert_any_call("Found matching projects", count=1, user_id=42)

    async def test_handle_regional_scenario_created_scenario_not_found(self, service, mock_client, mock_logger):
        event = RegionalScenarioCreated(scenario_id=5, territory_id=100)
        mock_client.get_scenario_by_id.side_effect = EntityNotFound

        await service.handle_regional_scenario_created(event)

        mock_logger.awarning.assert_called_once_with("Scenario not found", scenario_id=5)

    async def test_handle_regional_scenario_created_project_creation_bad_request(
        self, service, mock_client, mock_logger
    ):
        event = RegionalScenarioCreated(scenario_id=5, territory_id=100)

        scenario = AsyncMock()
        scenario.scenario_id = 5
        scenario.project.user_id = 42
        mock_client.get_scenario_by_id.return_value = scenario

        project = AsyncMock()
        project.project_id = 1
        project.user_id = 42
        mock_client.get_projects.return_value = [project]

        mock_client.create_base_scenario.side_effect = BadRequest("Invalid input")

        await service.handle_regional_scenario_created(event)

        mock_logger.aerror.assert_called_with(
            "Failed to create base scenario",
            project_id=1,
            regional_scenario_id=5,
            error="Invalid input",
        )
