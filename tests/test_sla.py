"""Tests for SLA calculations, breach detection, agent tools, and REST API."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from helpdesk.config import Settings
from helpdesk.tickets.repository import Priority, Status, Ticket, TicketRepository
from helpdesk.tickets.sla import (
    build_sla_router,
    check_sla_breaches_tool,
    find_breaches,
    sla_hours,
    sla_status,
)


@pytest.fixture
def custom_settings() -> Settings:
    return Settings(
        sla_hours_critical=2.0,
        sla_hours_high=6.0,
        sla_hours_medium=12.0,
        sla_hours_low=48.0,
    )


def test_sla_hours_defaults_and_custom(custom_settings: Settings) -> None:
    # Default settings
    assert sla_hours(Priority.CRITICAL) == 4.0
    assert sla_hours(Priority.HIGH) == 8.0
    assert sla_hours(Priority.MEDIUM) == 24.0
    assert sla_hours(Priority.LOW) == 72.0
    assert sla_hours("critical") == 4.0

    # Custom settings
    assert sla_hours(Priority.CRITICAL, custom_settings) == 2.0
    assert sla_hours(Priority.HIGH, custom_settings) == 6.0
    assert sla_hours(Priority.MEDIUM, custom_settings) == 12.0
    assert sla_hours(Priority.LOW, custom_settings) == 48.0


def test_sla_status_not_breached() -> None:
    created = datetime(2026, 11, 1, 10, 0, 0, tzinfo=UTC)
    now = datetime(2026, 11, 1, 12, 0, 0, tzinfo=UTC)
    ticket = Ticket(
        id=1001,
        title="VPN down",
        requester="alice",
        priority=Priority.HIGH,  # 8h SLA -> due 18:00 UTC
        status=Status.OPEN,
        created_at=created,
    )

    st = sla_status(ticket, now=now)
    assert st["key"] == "TCK-1001"
    assert st["priority"] == "high"
    assert st["status"] == "open"
    assert st["breached"] is False
    assert st["hours_remaining"] == 6.0
    assert st["created_at"] == created.isoformat()
    assert st["due_at"] == (created + timedelta(hours=8)).isoformat()


def test_sla_status_breached() -> None:
    created = datetime(2026, 11, 1, 10, 0, 0, tzinfo=UTC)
    now = datetime(2026, 11, 1, 19, 30, 0, tzinfo=UTC)  # 1.5h overdue
    ticket = Ticket(
        id=1002,
        title="Server reboot",
        requester="bob",
        priority=Priority.HIGH,  # 8h SLA -> due 18:00 UTC
        status=Status.OPEN,
        created_at=created,
    )

    st = sla_status(ticket, now=now)
    assert st["breached"] is True
    assert st["hours_remaining"] == -1.5


def test_sla_status_resolved_and_closed_never_breached() -> None:
    created = datetime(2026, 11, 1, 10, 0, 0, tzinfo=UTC)
    now = datetime(2026, 11, 10, 12, 0, 0, tzinfo=UTC)  # Many days later

    resolved_ticket = Ticket(
        id=1003,
        title="Printer fixed",
        requester="carol",
        priority=Priority.CRITICAL,  # 4h SLA
        status=Status.RESOLVED,
        created_at=created,
    )
    closed_ticket = Ticket(
        id=1004,
        title="Password reset done",
        requester="dave",
        priority=Priority.HIGH,
        status=Status.CLOSED,
        created_at=created,
    )

    st_res = sla_status(resolved_ticket, now=now)
    assert st_res["breached"] is False

    st_close = sla_status(closed_ticket, now=now)
    assert st_close["breached"] is False


def test_find_breaches_sorting_and_filtering(repo: TicketRepository) -> None:
    # Clear existing tickets to have strict control over SLA breach test
    frozen_now = datetime(2026, 11, 2, 12, 0, 0, tzinfo=UTC)

    # Ticket 1: Critical (4h SLA), created 10 hours ago -> 6 hours overdue
    t1 = repo.create("Emergency outage", "Down", "alice", Priority.CRITICAL)
    t1.created_at = frozen_now - timedelta(hours=10)

    # Ticket 2: High (8h SLA), created 9 hours ago -> 1 hour overdue
    t2 = repo.create("High priority issue", "Slow", "bob", Priority.HIGH)
    t2.created_at = frozen_now - timedelta(hours=9)

    # Ticket 3: Low (72h SLA), created 10 hours ago -> NOT overdue
    t3 = repo.create("Software install", "Acrobat", "carol", Priority.LOW)
    t3.created_at = frozen_now - timedelta(hours=10)

    # Ticket 4: Critical (4h SLA), created 10 hours ago, but RESOLVED -> NOT breached
    t4 = repo.create("Resolved outage", "Fixed", "dave", Priority.CRITICAL)
    t4.created_at = frozen_now - timedelta(hours=10)
    repo.update_status(t4.key, Status.RESOLVED)

    # Ticket 5: Medium (24h SLA), created 34 hours ago, IN_PROGRESS -> 10 hours overdue
    t5 = repo.create("Drive access", "Perms", "eve", Priority.MEDIUM)
    t5.created_at = frozen_now - timedelta(hours=34)
    repo.update_status(t5.key, Status.IN_PROGRESS)

    with repo.engine.begin() as conn:
        # Commit updated created_at timestamps into sqlite
        for t in (t1, t2, t3, t4, t5):
            conn.exec_driver_sql(
                "UPDATE ticket SET created_at = ? WHERE id = ?", (t.created_at, t.id)
            )

    breaches = find_breaches(repo, now=frozen_now)
    breached_keys = [b["key"] for b in breaches]

    # Only open/in_progress overdue tickets are breaches
    assert t1.key in breached_keys
    assert t2.key in breached_keys
    assert t5.key in breached_keys
    assert t3.key not in breached_keys
    assert t4.key not in breached_keys

    # Sorted most overdue first (most negative hours_remaining first)
    # t5 is 10h overdue (-10.0), t1 is 6h overdue (-6.0), t2 is 1h overdue (-1.0)
    assert breached_keys.index(t5.key) < breached_keys.index(t1.key)
    assert breached_keys.index(t1.key) < breached_keys.index(t2.key)


def test_check_sla_breaches_tool(repo: TicketRepository) -> None:
    result = check_sla_breaches_tool(repo)
    assert "count" in result
    assert "breaches" in result
    assert isinstance(result["count"], int)
    assert isinstance(result["breaches"], list)
    assert result["count"] == len(result["breaches"])


def test_sla_router(repo: TicketRepository) -> None:
    app = FastAPI()
    app.include_router(build_sla_router(repo))
    client = TestClient(app)

    # GET /sla/breaches
    resp_breaches = client.get("/sla/breaches")
    assert resp_breaches.status_code == 200
    assert isinstance(resp_breaches.json(), list)

    # GET /sla/tickets/{key} for existing ticket
    t = repo.search(limit=1)[0]
    resp_ticket = client.get(f"/sla/tickets/{t.key}")
    assert resp_ticket.status_code == 200
    data = resp_ticket.json()
    assert data["key"] == t.key
    for field in ("priority", "status", "created_at", "due_at", "hours_remaining", "breached"):
        assert field in data

    # GET /sla/tickets/{key} for non-existent ticket
    resp_missing = client.get("/sla/tickets/TCK-99999")
    assert resp_missing.status_code == 404
