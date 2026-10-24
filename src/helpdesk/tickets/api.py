"""REST API for the mock ticketing system (useful for dashboards, demos and debugging).

Run standalone: uvicorn helpdesk.tickets.api:create_app --factory --port 8001
(The main API in helpdesk.api.main also mounts these routes under /tickets.)
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel

from helpdesk.config import get_settings
from helpdesk.tickets.portal import build_portal_router
from helpdesk.tickets.repository import (
    Priority,
    Status,
    TicketNotFound,
    TicketRepository,
    comment_to_dict,
    ticket_to_dict,
)


class TicketCreate(BaseModel):
    title: str
    description: str = ""
    requester: str
    priority: Priority = Priority.MEDIUM
    category: str = "General"


class CommentCreate(BaseModel):
    body: str
    author: str = "api"


class StatusUpdate(BaseModel):
    status: Status
    note: str | None = None


def build_router(repo: TicketRepository) -> APIRouter:
    router = APIRouter(prefix="/tickets", tags=["tickets"])

    def not_found(e: TicketNotFound) -> HTTPException:
        return HTTPException(status_code=404, detail=str(e))

    @router.get("")
    def list_tickets(
        q: str | None = None, status: Status | None = None, requester: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        return [ticket_to_dict(t) for t in repo.search(q, status, requester, limit)]

    @router.get("/{key}")
    def get_ticket(key: str) -> dict[str, Any]:
        try:
            t = repo.get(key)
            return {**ticket_to_dict(t), "comments": [comment_to_dict(c) for c in repo.comments(key)]}
        except TicketNotFound as e:
            raise not_found(e) from e

    @router.post("", status_code=201)
    def create_ticket(body: TicketCreate) -> dict[str, Any]:
        t = repo.create(body.title, body.description, body.requester, body.priority, body.category)
        return ticket_to_dict(t)

    @router.post("/{key}/comments", status_code=201)
    def add_comment(key: str, body: CommentCreate) -> dict[str, Any]:
        try:
            return comment_to_dict(repo.add_comment(key, body.body, body.author))
        except TicketNotFound as e:
            raise not_found(e) from e

    @router.patch("/{key}/status")
    def update_status(key: str, body: StatusUpdate) -> dict[str, Any]:
        try:
            return ticket_to_dict(repo.update_status(key, body.status, body.note))
        except TicketNotFound as e:
            raise not_found(e) from e

    return router


def create_app(repo: TicketRepository | None = None) -> FastAPI:
    repo = repo or TicketRepository.from_path(get_settings().tickets_db)
    app = FastAPI(title="Mock Ticket API", version="0.1.0")
    app.include_router(build_router(repo))
    app.include_router(build_portal_router(repo))
    return app
