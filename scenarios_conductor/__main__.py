"""
This module initializes and starts the Kafka consumer service for scenario handling.
It loads configuration, sets up logging, registers message handlers, and optionally
starts a Prometheus metrics server.

The service listens to Kafka events and processes them using the registered handlers.
"""

import asyncio
import os

from dotenv import load_dotenv
from otteroad import KafkaConsumerService, KafkaConsumerSettings
from prometheus_client import start_http_server

from scenarios_conductor.config import AppConfig
from scenarios_conductor.handlers import handlers_list
from scenarios_conductor.services import BaseScenarioService, ProjectCadastreService
from scenarios_conductor.urban_client import make_http_client
from scenarios_conductor.utils.logging import configure_logging
from scenarios_conductor.utils.minio import download_from_minio

# Load environment variables from .env file or from the specified path
load_dotenv(os.getenv("ENVFILE", ".env"))


async def main_async() -> None:
    """The Main asynchronous entry point for launching the Kafka consumer service."""
    # Load application configuration from YAML or defaults
    app_config = AppConfig.from_file_or_default(os.getenv("CONFIG_PATH"))

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

    # Download the cadastre file from Minio
    await logger.ainfo("Downloading cadastre file from Minio...", file=app_config.fileserver.cadastre_path)
    cadastre_file_path = download_from_minio(app_config.fileserver, app_config.fileserver.cadastre_path, logger)

    # Initialize Kafka consumer settings and service
    kafka_settings = KafkaConsumerSettings.from_custom_config(app_config.broker)
    consumer = KafkaConsumerService(consumer_settings=kafka_settings, logger=logger)

    # Create shared HTTP client for urban API
    urban_api_client = await make_http_client(
        host=app_config.urban_api.host,
        auth_config=app_config.urban_api.auth.to_keycloak_token_config(),
        ping_timeout_seconds=app_config.urban_api.ping_timeout_seconds,
        operation_timeout_seconds=app_config.urban_api.operation_timeout_seconds,
    )

    # Register all message handlers with the consumer
    scenario_service = BaseScenarioService(urban_api_client, logger=logger)
    cadastre_service = ProjectCadastreService(urban_api_client, cadastre_file_path, logger=logger)
    for handler_class in handlers_list:
        if handler_class.__name__ == "ProjectCreatedHandler":
            handler = handler_class(scenario_service, cadastre_service, logger=logger)
        else:
            handler = handler_class(scenario_service, logger=logger)
        consumer.register_handler(handler)

    # Start the Kafka consumer worker
    await consumer.add_worker("scenario.events").start()

    # Keep the main loop alive until interrupted
    try:
        while True:
            await asyncio.sleep(10)
    except (KeyboardInterrupt, asyncio.CancelledError):
        # Graceful shutdown on interrupt
        await urban_api_client.close()
        await consumer.stop()

        # Clean up a temporary file
        if os.path.exists(cadastre_file_path):
            os.remove(cadastre_file_path)
            await logger.ainfo("Temporary cadastre file removed")


def main() -> None:
    """Synchronous entry point to run the asynchronous main logic."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
