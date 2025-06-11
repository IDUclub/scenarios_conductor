"""Kafka event handlers are defined here."""

from .project_created import ProjectCreatedHandler
from .regional_scenario_created import RegionalScenarioCreatedHandler

handlers_list = [
    ProjectCreatedHandler,
    RegionalScenarioCreatedHandler,
]


__all__ = [
    "handlers_list",
]
