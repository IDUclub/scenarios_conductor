"""
This module provides a `configure_logging` function for setting up structured logging
with `structlog`. It supports console and file logging, with different log levels
per output destination.

Usage:
    from logging_config import configure_logging

    logger = configure_logging(
        log_level="DEBUG",
        files={"app.log": "INFO"},
        root_logger_level="INFO"
    )
    logger.info("Application started")
"""

import logging
import sys
from typing import Literal

import structlog

# Literal type for supported logging levels
LoggingLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def configure_logging(
    log_level: LoggingLevel,
    files: dict[str, LoggingLevel] | None = None,
    root_logger_level: LoggingLevel = "INFO",
) -> structlog.stdlib.BoundLogger:
    """
    Configures logging using structlog with optional file handlers and different log levels.

    Args:
        log_level (LoggingLevel): Log level for the structlog logger (e.g., "DEBUG", "INFO").
        files (dict[str, LoggingLevel] | None): Mapping of log file paths to their respective log levels.
        root_logger_level (LoggingLevel): Log level for the root logger.

    Returns:
        structlog.stdlib.BoundLogger: Configured logger instance.
    """
    # Mapping string log levels to logging module constants
    level_name_mapping = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    # Fallback to empty dict if no file configuration is provided
    files = files or {}

    # Configure structlog processors and logger factory
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,  # Merge context variables
            structlog.stdlib.add_log_level,  # Add log level to log record
            structlog.stdlib.add_logger_name,  # Add logger name
            structlog.processors.TimeStamper(fmt="iso"),  # Add ISO timestamp
            structlog.processors.StackInfoRenderer(),  # Render stack info if available
            structlog.processors.format_exc_info,  # Format exception info
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,  # Wrap formatter for stdlib logging
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Create main application logger
    logger: structlog.stdlib.BoundLogger = structlog.get_logger("main")
    logger.setLevel(level_name_mapping[log_level])

    # Create console (stderr) handler with pretty renderer
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(processor=structlog.dev.ConsoleRenderer(colors=True))
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(console_handler)

    # Configure file handlers for each configured file path
    for filename, level in files.items():
        file_handler = logging.FileHandler(filename=filename, encoding="utf-8")
        file_handler.setFormatter(structlog.stdlib.ProcessorFormatter(processor=structlog.processors.JSONRenderer()))
        file_handler.setLevel(level_name_mapping[level])
        root_logger.addHandler(file_handler)

    # Set the root logger level
    root_logger.setLevel(level_name_mapping[root_logger_level])

    return logger
