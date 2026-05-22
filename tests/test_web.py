"""Tests for the FastAPI web UI."""
from __future__ import annotations

import sqlite3

import pytest
from httpx import ASGITransport, AsyncClient

from courant.repository import migrate
from courant.service import ReminderService
from courant.web import create_app


@pytest.fixture
def app_with_empty_db(memory_db: sqlite3.Connection):
    migrate(memory_db)
    service = ReminderService(memory_db)
    return create_app(service)


async def test_health_endpoint(app_with_empty_db):
    async with AsyncClient(transport=ASGITransport(app=app_with_empty_db), base_url="http://test") as client:
        resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_dashboard_renders(app_with_empty_db):
    async with AsyncClient(transport=ASGITransport(app=app_with_empty_db), base_url="http://test") as client:
        resp = await client.get("/")
    assert resp.status_code == 200
    assert "Courant" in resp.text
    assert "text/html" in resp.headers["content-type"]
