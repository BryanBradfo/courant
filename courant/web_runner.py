"""Helpers to run the FastAPI app via uvicorn.

Kept separate from web.py so `web.py` stays pure FastAPI / no uvicorn config —
testable with httpx.AsyncClient without spinning a real server.
"""
from __future__ import annotations

import logging

import uvicorn

from courant.events_bus import EventBus
from courant.service import ReminderService
from courant.web import create_app

logger = logging.getLogger(__name__)


def run_server(
    service: ReminderService,
    host: str = "127.0.0.1",
    port: int = 8765,
    bus: EventBus | None = None,
) -> None:
    """Block until uvicorn shuts down (SIGINT/SIGTERM)."""
    app = create_app(service, bus=bus)
    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        log_level="info",
        access_log=False,  # very noisy at every HTMX poll
    )
    server = uvicorn.Server(config)
    logger.info("Web UI listening on http://%s:%d", host, port)
    server.run()
