"""The utilities for starting and stopping the prometheus server are here."""

from prometheus_client import start_http_server

_server, _thread = None, None


def start_server(port: int = 8000):
    """Start the prometheus server."""
    global _server, _thread  # pylint: disable=global-statement
    _server, _thread = start_http_server(port)


def stop_server():
    """Stop the prometheus server."""
    if _server is not None:
        _server.shutdown()
