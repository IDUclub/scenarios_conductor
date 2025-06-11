"""
This module contains the BaseScenarioService class, which is responsible for handling
Kafka events related to the creation of projects and regional scenarios. Based on these
events, it interacts with the UrbanClient to create corresponding base scenarios.

Supported event handlers:
- handle_project_created: triggered when a new project is created.
- handle_regional_scenario_created: triggered when a new regional scenario is created.
"""

import structlog
from otteroad.models import ProjectCreated, RegionalScenarioCreated

from scenarios_conductor.urban_client import UrbanClient
from scenarios_conductor.urban_client.http.exceptions import BadRequest, ConflictAlreadyExists, EntityNotFound


class BaseScenarioService:
    """Service for handling base scenario creation logic based on project and regional scenario events."""

    def __init__(self, urban_client: UrbanClient, logger: structlog.stdlib.BoundLogger):
        """
        Initializes the service with an UrbanClient and a logger.

        Args:
            urban_client (UrbanClient): Client for interacting with the urban API.
            logger (structlog.stdlib.BoundLogger): Logger instance for structured logging.
        """
        self._urban_client = urban_client
        self._logger = logger

    async def handle_project_created(self, event: ProjectCreated):
        """
        Handles the ProjectCreated event.

        When a new project is created, this method finds all regional scenarios
        of the same user and creates a base scenario for each if one doesn't already exist.

        Args:
            event (ProjectCreated): The incoming event with project and territory IDs.
        """
        try:
            project = await self._urban_client.get_project_by_id(event.project_id)
        except EntityNotFound:
            await self._logger.awarning("Project not found", project_id=event.project_id)
            return
        except Exception:
            await self._logger.aerror("Failed to fetch project", project_id=event.project_id)
            raise

        user_id = project.user_id

        try:
            regional_scenarios = await self._urban_client.get_scenarios(territory_id=event.territory_id)
        except EntityNotFound:
            await self._logger.awarning("No territory found", project_id=event.project_id)
            return
        except Exception:
            await self._logger.aerror("Failed to fetch regional scenarios", territory_id=event.territory_id)
            raise

        # Filter scenarios that belong to the same user and are not already based
        filtered = [s for s in regional_scenarios if s.project.user_id == user_id and not s.is_based]
        await self._logger.ainfo("Found matching regional scenarios", count=len(filtered), user_id=user_id)

        # Attempt to create a base scenario for each matching regional scenario
        for scenario in filtered:
            try:
                base_scenario = await self._urban_client.create_base_scenario(
                    project_id=event.project_id, scenario_id=scenario.scenario_id
                )
                await self._logger.ainfo(
                    "Base scenario created for project",
                    project_id=event.project_id,
                    regional_scenario_id=scenario.scenario_id,
                    base_scenario_id=base_scenario.scenario_id,
                )
            except ConflictAlreadyExists:
                await self._logger.awarning(
                    "Base scenario already exists",
                    project_id=event.project_id,
                    regional_scenario_id=scenario.scenario_id,
                )
            except (EntityNotFound, BadRequest) as exc:
                await self._logger.aerror(
                    "Failed to create base scenario",
                    project_id=event.project_id,
                    regional_scenario_id=scenario.scenario_id,
                    error=str(exc),
                )
            except Exception:
                await self._logger.aerror(
                    "Unexpected error while creating base scenario",
                    project_id=event.project_id,
                    regional_scenario_id=scenario.scenario_id,
                )
                raise

    async def handle_regional_scenario_created(self, event: RegionalScenarioCreated):
        """
        Handles the RegionalScenarioCreated event.

        When a new regional scenario is created, this method finds all projects
        of the same user in the territory and creates base scenarios for them.

        Args:
            event (RegionalScenarioCreated): The incoming event with scenario and territory IDs.
        """
        try:
            scenario = await self._urban_client.get_scenario_by_id(event.scenario_id)
        except EntityNotFound:
            await self._logger.awarning("Scenario not found", scenario_id=event.scenario_id)
            return
        except Exception:
            await self._logger.aerror("Failed to fetch scenario", scenario_id=event.scenario_id)
            raise

        user_id = scenario.project.user_id

        try:
            projects = await self._urban_client.get_projects(territory_id=event.territory_id)
        except EntityNotFound:
            await self._logger.awarning("No territory found", territory_id=event.territory_id)
            return
        except Exception:
            await self._logger.aerror("Failed to fetch projects", territory_id=event.territory_id)
            raise

        filtered = [p for p in projects if p.user_id == user_id]
        await self._logger.ainfo("Found matching projects", count=len(filtered), user_id=user_id)

        # Attempt to create a base scenario for each project
        for project in filtered:
            try:
                base_scenario = await self._urban_client.create_base_scenario(
                    project_id=project.project_id,
                    scenario_id=event.scenario_id,
                )
                await self._logger.ainfo(
                    "Base scenario created",
                    project_id=project.project_id,
                    regional_scenario_id=scenario.scenario_id,
                    base_scenario_id=base_scenario.scenario_id,
                )
            except ConflictAlreadyExists:
                await self._logger.awarning(
                    "Base scenario already exists",
                    project_id=project.project_id,
                    regional_scenario_id=scenario.scenario_id,
                )
            except (EntityNotFound, BadRequest) as exc:
                await self._logger.aerror(
                    "Failed to create base scenario",
                    project_id=project.project_id,
                    regional_scenario_id=scenario.scenario_id,
                    error=str(exc),
                )
            except Exception:
                await self._logger.aerror(
                    "Unexpected error while creating base scenario",
                    project_id=project.project_id,
                    regional_scenario_id=scenario.scenario_id,
                )
                raise
