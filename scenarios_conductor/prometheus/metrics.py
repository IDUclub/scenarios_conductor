"""All prometheus metrics are defined here."""

from prometheus_client import Counter, Histogram

PROJECT_CREATED_EVENTS_TOTAL = Counter(
    "project_created_events_total",
    "Total number of ProjectCreated events received",
)

PROJECT_CREATED_SUCCESS_TOTAL = Counter(
    "project_created_success_total",
    "Total number of ProjectCreated events successfully processed",
)

PROJECT_CREATED_ERROR_TOTAL = Counter(
    "project_created_error_total",
    "Total number of ProjectCreated events that failed during processing",
)

PROJECT_CREATED_DURATION_SECONDS = Histogram(
    "project_created_duration_seconds",
    "Duration of ProjectCreated event processing",
    buckets=(0.1, 0.2, 0.5, 1, 2, 5, 10, 30, 60, 120),
)


REGIONAL_SCENARIO_CREATED_EVENTS_TOTAL = Counter(
    "regional_scenario_created_events_total",
    "Total number of ProjectCreated events received",
)

REGIONAL_SCENARIO_CREATED_SUCCESS_TOTAL = Counter(
    "regional_scenario_created_success_total",
    "Total number of ProjectCreated events successfully processed",
)

REGIONAL_SCENARIO_CREATED_ERROR_TOTAL = Counter(
    "regional_scenario_created_error_total",
    "Total number of ProjectCreated events that failed during processing",
)

REGIONAL_SCENARIO_CREATED_DURATION_SECONDS = Histogram(
    "regional_scenario_created_duration_seconds",
    "Duration of ProjectCreated event processing",
    buckets=(0.1, 0.2, 0.5, 1, 2, 5, 10, 30, 60, 120),
)
