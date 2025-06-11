"""
This module defines the RegionalScenarioCreatedHandler class,
responsible for handling `RegionalScenarioCreatedHandler` Kafka events.

It uses Prometheus metrics to track the number, success, duration, and errors of event handling,
and delegates the actual processing to the BaseScenarioService.
"""

import time

import structlog
from confluent_kafka import Message
from otteroad import BaseMessageHandler
from otteroad.models import RegionalScenarioCreated

from scenarios_conductor.prometheus.metrics import (
    REGIONAL_SCENARIO_CREATED_DURATION_SECONDS,
    REGIONAL_SCENARIO_CREATED_ERROR_TOTAL,
    REGIONAL_SCENARIO_CREATED_EVENTS_TOTAL,
    REGIONAL_SCENARIO_CREATED_SUCCESS_TOTAL,
)
from scenarios_conductor.services import BaseScenarioService


class RegionalScenarioCreatedHandler(BaseMessageHandler[RegionalScenarioCreated]):
    """
    Handler for processing RegionalScenarioCreated events.

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
        self._metadata = {}

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
        event: RegionalScenarioCreated,
        ctx: Message,
        *args,
        **kwargs,
    ) -> tuple[RegionalScenarioCreated, Message]:
        """
        Called before handling the event. Increments the event counter
        and starts timing the operation.

        Args:
            event (RegionalScenarioCreated): Incoming deserialized event.
            ctx (Message): Raw Kafka message context.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            Tuple[RegionalScenarioCreated, Message]: The same event and context.
        """
        REGIONAL_SCENARIO_CREATED_EVENTS_TOTAL.inc()
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
            REGIONAL_SCENARIO_CREATED_DURATION_SECONDS.observe(duration)
        REGIONAL_SCENARIO_CREATED_SUCCESS_TOTAL.inc()
        return await super().post_process(*args, **kwargs)

    async def handle_error(
        self,
        error: Exception,
        event: RegionalScenarioCreated,
        ctx: Message,
        *args,
        **kwargs,
    ) -> None:
        """
        Called if an exception occurs during processing.
        Increments the error counter.

        Args:
            error (Exception): The raised exception.
            event (RegionalScenarioCreated): The event being processed.
            ctx (Message): The original Kafka message context.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.
        """
        REGIONAL_SCENARIO_CREATED_ERROR_TOTAL.inc()
        return await super().handle_error(error, event, ctx, *args, **kwargs)

    async def handle(self, event: RegionalScenarioCreated, ctx: Message):
        """
        Main event handler logic. Delegates base scenario creation to the service.

        Args:
            event (RegionalScenarioCreated): The deserialized regional scenario created event.
            ctx (Message): The original Kafka message.
        """
        await self._service.handle_regional_scenario_created(event)
