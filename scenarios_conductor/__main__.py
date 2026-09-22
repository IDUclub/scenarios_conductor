"""
This module initializes and starts the Kafka consumer service for scenario handling.
It loads configuration, sets up logging, registers message handlers, and optionally
starts a Prometheus metrics server.

The service listens to Kafka events and processes them using the registered handlers.
"""

import asyncio
import os
import signal
from pathlib import Path

from dotenv import load_dotenv
from otteroad import KafkaConsumerService, KafkaConsumerSettings
from prometheus_client import start_http_server

from scenarios_conductor.config import AppConfig
from scenarios_conductor.handlers import handlers_list
from scenarios_conductor.services import BaseScenarioService, ProjectCadastreService
from scenarios_conductor.urban_client import make_http_client
from scenarios_conductor.utils.logging import configure_logging

# Load environment variables from .env file or from the specified path
load_dotenv(os.getenv("ENVFILE", ".env"))


async def main_async() -> None:
    """The Main asynchronous entry point for launching the Kafka consumer service."""
    # Load application configuration from YAML or defaults
    app_config = AppConfig.from_file_or_default(os.getenv("CONFIG_PATH"))

    cadastre_file_path = Path(app_config.cadastre.path)
    if not cadastre_file_path.is_file():
        raise FileNotFoundError(
            f"Cadastre file not found: {cadastre_file_path}. Check cadastre.path and the Docker bind mount."
        )

    # Configure application logging
    loggers_dict = {logger_config.filename: logger_config.level for logger_config in app_config.logging.files}
    logger = configure_logging(
        app_config.logging.level,
        loggers_dict,
        root_logger_level=app_config.logging.level,
    )

    # Start Prometheus metrics server if not disabled in config
    if not app_config.prometheus.disable:
        start_http_server(app_config.prometheus.port)
        await logger.ainfo("Prometheus metrics server started", port=app_config.prometheus.port)

    kafka_settings = KafkaConsumerSettings.from_custom_config(app_config.broker)
    consumer = KafkaConsumerService(consumer_settings=kafka_settings, logger=logger)
    urban_api_client = None
    try:  # pylint: disable=too-many-try-statements
        urban_api_client = await make_http_client(
            host=app_config.urban_api.host,
            auth_config=app_config.urban_api.auth.to_keycloak_token_config(),
            ping_timeout_seconds=app_config.urban_api.ping_timeout_seconds,
            operation_timeout_seconds=app_config.urban_api.operation_timeout_seconds,
        )
        scenario_service = BaseScenarioService(urban_api_client, logger=logger)
        await logger.ainfo("Opening local cadastre", path=str(cadastre_file_path))
        cadastre_service = ProjectCadastreService(urban_api_client, str(cadastre_file_path), logger=logger)

        for handler_class in handlers_list:
            if handler_class.__name__ == "ProjectCreatedHandler":
                handler = handler_class(scenario_service, cadastre_service, logger=logger)
            else:
                handler = handler_class(scenario_service, logger=logger)
            consumer.register_handler(handler)

        await consumer.add_worker("scenario.events").start()
        while True:
            await asyncio.sleep(10)
    finally:
        try:
            await consumer.stop()
        finally:
            if urban_api_client is not None:
                await urban_api_client.close()


def main() -> None:
    """Synchronous entry point to run the asynchronous main logic."""

    def interrupt(_signum, _frame):
        # Docker sends SIGTERM. Interrupt startup as well as the loop.
        raise KeyboardInterrupt

    previous_handler = signal.signal(signal.SIGTERM, interrupt)
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        pass
    finally:
        signal.signal(signal.SIGTERM, previous_handler)


if __name__ == "__main__":
    main()
