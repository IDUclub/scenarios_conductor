"""Urban_api client is located here. There is a possibility it will move to an individual package."""

import structlog.stdlib
from idu_service_auth import KeycloakTokenClient, KeycloakTokenConfig

from ._abstract import UrbanClient
from .http import HTTPUrbanClient

__all__ = [
    "UrbanClient",
    "make_http_client",
]


async def make_http_client(
    host: str,
    auth_config: KeycloakTokenConfig,
    *,
    ping_timeout_seconds: float = 2.0,
    operation_timeout_seconds: float = 60.0,
    logger: structlog.stdlib.BoundLogger = ...,
) -> UrbanClient:
    """Get HTTP Urban API client."""
    client = HTTPUrbanClient(
        host,
        auth_client=KeycloakTokenClient(auth_config),
        ping_timeout_seconds=ping_timeout_seconds,
        operation_timeout_seconds=operation_timeout_seconds,
        logger=logger,
    )
    await client.start()
    return client
