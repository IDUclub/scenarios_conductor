"""
This module defines the ProjectCreatedHandler class, responsible for handling `ProjectCreated` Kafka events.

It uses Prometheus metrics to track the number, success, duration, and errors of event handling,
and delegates the actual processing to the BaseScenarioService.
"""

import time
from typing import Any

import structlog.stdlib
from confluent_kafka import Message
from otteroad import BaseMessageHandler
from otteroad.models import ProjectCreated

from scenarios_conductor.prometheus.metrics import (
    PROJECT_CREATED_DURATION_SECONDS,
    PROJECT_CREATED_ERROR_TOTAL,
    PROJECT_CREATED_EVENTS_TOTAL,
    PROJECT_CREATED_SUCCESS_TOTAL,
)
from scenarios_conductor.services import BaseScenarioService


class ProjectCreatedHandler(BaseMessageHandler[ProjectCreated]):
    """
    Handler for processing ProjectCreated events.

    This handler tracks metrics, measures processing time, and delegates
    the creation of base scenarios to the service layer.
    """

    def __init__(self, service: BaseScenarioService, logger: structlog.stdlib.BoundLogger):
        """
        Initialize the handler with a service instance and logger.

        Args:
            service (BaseScenarioService): Service that handles business logic.
            logger (structlog.stdlib.BoundLogger): Logger for structured logging.
        """
        super().__init__(logger)
        self._service = service
        self._metadata: dict[str, Any] = {}

    async def on_startup(self):
        """
        Optional startup logic placeholder.
        Called once when the handler is initialized.
        """

    async def on_shutdown(self):
        """
        Optional shutdown logic placeholder.
        Called once when the handler is shutting down.
        """

    async def pre_process(
        self,
        event: ProjectCreated,
        ctx: Message,
        *args,
        **kwargs,
    ) -> tuple[ProjectCreated, Message]:
        """
        Called before handling the event. Increments the event counter
        and starts timing the operation.

        Args:
            event (ProjectCreated): Incoming deserialized event.
            ctx (Message): Raw Kafka message context.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            Tuple[ProjectCreated, Message]: The same event and context.
        """
        PROJECT_CREATED_EVENTS_TOTAL.inc()
        self._metadata["start_time"] = time.perf_counter()
        return await super().pre_process(event, ctx, *args, **kwargs)

    async def post_process(self, *args, **kwargs):
        """
        Called after successful handling of the event.
        Tracks the duration and increments the success counter.
        """
        start_time = self._metadata.pop("start_time", None)
        if start_time is not None:
            duration = time.perf_counter() - start_time
            PROJECT_CREATED_DURATION_SECONDS.observe(duration)

        PROJECT_CREATED_SUCCESS_TOTAL.inc()
        return await super().post_process(*args, **kwargs)

    async def handle_error(
        self,
        error: Exception,
        event: ProjectCreated,
        ctx: Message,
        *args,
        **kwargs,
    ) -> None:
        """
        Called if an exception occurs during processing.
        Increments the error counter.

        Args:
            error (Exception): The raised exception.
            event (ProjectCreated): The event being processed.
            ctx (Message): The original Kafka message context.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.
        """
        PROJECT_CREATED_ERROR_TOTAL.inc()
        return await super().handle_error(error, event, ctx, *args, **kwargs)

    async def handle(self, event: ProjectCreated, ctx: Message):
        """
        Main event handler logic. Delegates base scenario creation to the service.

        Args:
            event (ProjectCreated): The deserialized project created event.
            ctx (Message): The original Kafka message.
        """
        await self._service.handle_project_created(event)
