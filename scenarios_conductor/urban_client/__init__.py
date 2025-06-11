"""Urban_api client is located here. There is a possibility it will move to an individual package."""

import structlog.stdlib

from ._abstract import UrbanClient
from .http import HTTPUrbanClient

__all__ = [
    "UrbanClient",
    "make_http_client",
]


def make_http_client(
    host: str,
    api_token: str,
    *,
    ping_timeout_seconds: float = 2.0,
    operation_timeout_seconds: float = 30.0,
    logger: structlog.stdlib.BoundLogger = ...,
) -> UrbanClient:
    """Get HTTP Urban API client."""
    client = HTTPUrbanClient(
        host,
        api_token=api_token,
        ping_timeout_seconds=ping_timeout_seconds,
        operation_timeout_seconds=operation_timeout_seconds,
        logger=logger,
    )
    client.start()
    return client
