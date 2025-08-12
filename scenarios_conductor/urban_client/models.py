"""Urban API models are defined here."""

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


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
