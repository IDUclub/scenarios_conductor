"""
This module defines application configuration using data classes.
It supports loading from and dumping to YAML, with structured logging,
Kafka broker, Prometheus, and external API configuration sections.
"""

import os
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import TextIO

import yaml

from .utils.logging import LoggingLevel


@dataclass
class FileLogger:
    """Represents file-based logging configuration."""

    filename: str
    level: LoggingLevel


@dataclass
class LoggingConfig:
    """Represents the logging configuration for the application."""

    level: LoggingLevel
    files: list[FileLogger] = field(default_factory=list)

    def __post_init__(self):
        # If `files` is loaded as a list of dicts (e.g., from YAML), convert to FileLogger instances.
        if self.files and isinstance(self.files[0], dict):
            self.files = [FileLogger(**f) for f in self.files]


@dataclass
class PrometheusConfig:
    """Represents Prometheus metrics configuration."""

    port: int = 9000
    disable: bool = False


@dataclass
class BrokerConfig:
    """Configuration for Kafka broker and Schema Registry."""

    client_id: str
    group_id: str
    bootstrap_servers: str
    schema_registry_url: str
    auto_offset_reset: str
    enable_auto_commit: bool


@dataclass
class UrbanAPIConfig:
    """Configuration for Urban API access."""

    host: str
    api_token: str


@dataclass
class AppConfig:
    """
    Main application configuration class.

    Combines all sub-configs and provides methods for serialization, deserialization, and merging.
    """

    name: str
    logging: LoggingConfig
    prometheus: PrometheusConfig
    broker: BrokerConfig
    urban_api: UrbanAPIConfig

    def to_order_dict(self) -> OrderedDict:
        """
        Convert this configuration to an OrderedDict recursively, suitable for YAML dumping.

        Returns:
            OrderedDict: Ordered representation of the config.
        """

        def to_ordered_dict_recursive(obj) -> OrderedDict:
            if isinstance(obj, (dict, OrderedDict)):
                return OrderedDict((k, to_ordered_dict_recursive(v)) for k, v in obj.items())
            if isinstance(obj, list):
                return [to_ordered_dict_recursive(item) for item in obj]
            if hasattr(obj, "__dataclass_fields__"):
                return OrderedDict(
                    (field, to_ordered_dict_recursive(getattr(obj, field))) for field in obj.__dataclass_fields__
                )
            return obj

        return OrderedDict(
            [
                ("name", self.name),
                ("logging", to_ordered_dict_recursive(self.logging)),
                ("prometheus", to_ordered_dict_recursive(self.prometheus)),
                ("broker", to_ordered_dict_recursive(self.broker)),
                ("urban_api", to_ordered_dict_recursive(self.urban_api)),
            ]
        )

    def dump(self, file: str | Path | TextIO) -> None:
        """
        Export the current configuration to a YAML file or stream.

        Args:
            file (str | Path | TextIO): Target file path or open file object.
        """

        class OrderedDumper(yaml.SafeDumper):
            """OrderedDump dump serializer."""

            def represent_dict_preserve_order(self, data):
                """Represent OrderedDict data as YAML dict."""
                return self.represent_dict(data.items())

        OrderedDumper.add_representer(OrderedDict, OrderedDumper.represent_dict_preserve_order)

        if isinstance(file, (str, Path)):
            with open(str(file), "w", encoding="utf-8") as file_w:
                yaml.dump(self.to_order_dict(), file_w, Dumper=OrderedDumper, default_flow_style=False)
        else:
            yaml.dump(self.to_order_dict(), file, Dumper=OrderedDumper, default_flow_style=False)

    @classmethod
    def example(cls) -> "AppConfig":
        """
        Generate a sample AppConfig instance for testing or default usage.

        Returns:
            AppConfig: Example configuration.
        """
        return cls(
            name="example app",
            logging=LoggingConfig(level="INFO", files=[FileLogger(filename="logs/info.log", level="INFO")]),
            prometheus=PrometheusConfig(port=9000, disable=False),
            broker=BrokerConfig(
                client_id="scenarios-conductor",
                group_id="scenarios-conductor-group",
                bootstrap_servers="localhost:9092",
                schema_registry_url="http://localhost:8100",
                auto_offset_reset="latest",
                enable_auto_commit=False,
            ),
            urban_api=UrbanAPIConfig(host="http://localhost:8100", api_token="token"),
        )

    @classmethod
    def load(cls, file: str | Path | TextIO) -> "AppConfig":
        """
        Load configuration from a YAML file or stream.

        Args:
            file (str | Path | TextIO): Path or open file stream to read from.

        Returns:
            AppConfig: Loaded configuration.

        Raises:
            ValueError: If the file can't be read or parsed.
        """
        try:
            if isinstance(file, (str, Path)):
                with open(file, "r", encoding="utf-8") as file_r:
                    data = yaml.safe_load(file_r)
            else:
                data = yaml.safe_load(file)

            return cls(
                name=data.get("name", "example app"),
                logging=LoggingConfig(**data.get("logging", {})),
                prometheus=PrometheusConfig(**data.get("prometheus", {})),
                broker=BrokerConfig(**data.get("broker", {})),
                urban_api=UrbanAPIConfig(**data.get("urban_api", {})),
            )
        except Exception as exc:
            print(exc)  # Can be replaced with structured logging if desired
            raise ValueError(f"Could not read app config file: {file}") from exc

    @classmethod
    def from_file_or_default(cls, config_path: str | None = os.getenv("CONFIG_PATH")) -> "AppConfig":
        """
        Load configuration from the provided file path or return a default example if not found.

        Args:
            config_path (str | None): File path to load config from (defaults to CONFIG_PATH env var).

        Returns:
            AppConfig: Loaded or fallback configuration.
        """
        if not config_path:
            return cls.example()
        return cls.load(config_path)

    def update(self, other: "AppConfig") -> None:
        """
        Update the current configuration with values from another AppConfig instance.

        Args:
            other (AppConfig): The configuration instance to merge from.
        """
        for section in ("logging", "prometheus", "broker", "urban_api"):
            current_subconfig = getattr(self, section)
            other_subconfig = getattr(other, section)

            for param, value in other_subconfig.__dict__.items():
                if param in current_subconfig.__dict__:
                    setattr(current_subconfig, param, value)
