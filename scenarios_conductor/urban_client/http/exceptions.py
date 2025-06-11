"""HTTP-specific exceptions are defined here."""

from scenarios_conductor.urban_client.exceptions import APIError


class InvalidStatusCode(APIError):
    """Got unexpected status code from API request."""


class BadRequest(APIError):
    """Got status code 400 'bad request` from API request."""


class EntityNotFound(APIError):
    """Got status code 404 'not found` from API request."""


class ConflictAlreadyExists(APIError):
    """Got status code 409 'already exists` from API request."""
