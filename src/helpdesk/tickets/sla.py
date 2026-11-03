"""SLA tracking, breach calculation, agent inspection tool, and REST API router."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, or_, select

from helpdesk.config import Settings, get_settings
from helpdesk.tickets.repository import (
    Priority,
    Status,
    Ticket,
    TicketNotFound,
    TicketRepository,
)


def sla_hours(priority: Priority | str, settings: Settings | None = None) -> float:
    """Return configured SLA target in hours for the given priority level."""
    s = settings or get_settings()
    p = Priority(str(priority).lower())
    if p == Priority.CRITICAL:
        return s.sla_hours_critical
    elif p == Priority.HIGH:
        return s.sla_hours_high
    elif p == Priority.MEDIUM:
        return s.sla_hours_medium
    elif p == Priority.LOW:
        return s.sla_hours_low
    return s.sla_hours_medium


def sla_status(
    ticket: Ticket,
    settings: Settings | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Calculate SLA due date, remaining time, and breach status for a ticket.

    Resolved and closed tickets are never marked as breached.
    """
    s = settings or get_settings()
    created_at = ticket.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)

    ref_now = now if now is not None else datetime.now(UTC)
    if ref_now.tzinfo is None:
        ref_now = ref_now.replace(tzinfo=UTC)

    hours = sla_hours(ticket.priority, s)
    due_at = created_at + timedelta(hours=hours)
    remaining_seconds = (due_at - ref_now).total_seconds()
    hours_remaining = round(remaining_seconds / 3600.0, 2)

    is_terminal = str(ticket.status).lower() in (
        Status.RESOLVED,
        Status.CLOSED,
        "resolved",
        "closed",
    )
    breached = False if is_terminal else (ref_now > due_at)

    return {
        "key": ticket.key,
        "priority": str(ticket.priority),
        "status": str(ticket.status),
        "created_at": created_at.isoformat(),
        "due_at": due_at.isoformat(),
        "hours_remaining": hours_remaining,
        "breached": breached,
    }


def find_breaches(
    repo: TicketRepository,
    settings: Settings | None = None,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """Find all active (open / in_progress) tickets breaching SLA, sorted most overdue first."""
    s = settings or get_settings()
    ref_now = now if now is not None else datetime.now(UTC)
    if ref_now.tzinfo is None:
        ref_now = ref_now.replace(tzinfo=UTC)

    if hasattr(repo, "engine"):
        with Session(repo.engine) as session:
            stmt = select(Ticket).where(
                or_(Ticket.status == Status.OPEN, Ticket.status == Status.IN_PROGRESS)
            )
            active_tickets = list(session.exec(stmt).all())
    else:
        open_tickets = repo.search(status=Status.OPEN, limit=10000)
        in_prog_tickets = repo.search(status=Status.IN_PROGRESS, limit=10000)
        active_tickets = open_tickets + in_prog_tickets

    breaches: list[dict[str, Any]] = []
    for t in active_tickets:
        st = sla_status(t, s, now=ref_now)
        if st["breached"]:
            breaches.append(st)

    # Sort most overdue first (most negative hours_remaining first)
    breaches.sort(key=lambda x: x["hours_remaining"])
    return breaches


def build_sla_router(repo: TicketRepository, settings: Settings | None = None) -> APIRouter:
    router = APIRouter(prefix="/sla", tags=["sla"])
    s = settings or get_settings()

    @router.get("/breaches")
    def get_breaches() -> list[dict[str, Any]]:
        return find_breaches(repo, s)

    @router.get("/tickets/{key}")
    def get_ticket_sla(key: str) -> dict[str, Any]:
        try:
            t = repo.get(key)
        except TicketNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return sla_status(t, s)

    return router


def check_sla_breaches_tool(repo: TicketRepository, settings: Settings | None = None) -> dict[str, Any]:
    """Agent tool callable to report current SLA breach count and details."""
    breaches = find_breaches(repo, settings)
    return {"count": len(breaches), "breaches": breaches}
