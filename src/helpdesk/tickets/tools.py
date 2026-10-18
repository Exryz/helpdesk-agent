"""Ticket tools: one implementation shared by the MCP server and the in-process backend.

Every tool returns a JSON-serialisable dict. Failures are returned as {"error": "..."}
instead of raised, so the LLM can read the problem and recover.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from helpdesk.tickets.repository import (
    Priority,
    Status,
    TicketNotFound,
    TicketRepository,
    comment_to_dict,
    ticket_to_dict,
)

STATUSES = [s.value for s in Status]
PRIORITIES = [p.value for p in Priority]


class TicketTools:
    def __init__(self, repo: TicketRepository):
        self.repo = repo

    def _safe(self, fn: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        try:
            return fn()
        except TicketNotFound as e:
            return {"error": str(e)}
        except ValueError as e:
            return {"error": f"Invalid input: {e}"}

    def search_tickets(
        self,
        query: str | None = None,
        status: str | None = None,
        requester: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Search tickets by keywords in title/description, status and/or requester."""

        def run() -> dict[str, Any]:
            tickets = self.repo.search(query or None, status or None, requester or None, limit)
            return {"count": len(tickets), "tickets": [ticket_to_dict(t) for t in tickets]}

        return self._safe(run)

    def get_ticket(self, ticket_key: str) -> dict[str, Any]:
        """Get one ticket (e.g. 'TCK-1003') with its comment history."""

        def run() -> dict[str, Any]:
            ticket = self.repo.get(ticket_key)
            return {
                **ticket_to_dict(ticket),
                "comments": [comment_to_dict(c) for c in self.repo.comments(ticket_key)],
            }

        return self._safe(run)

    def create_ticket(
        self,
        title: str,
        description: str,
        requester: str,
        priority: str = "medium",
        category: str = "General",
    ) -> dict[str, Any]:
        """Create a new support ticket."""
        return self._safe(
            lambda: {
                "created": True,
                **ticket_to_dict(
                    self.repo.create(title, description, requester, priority, category)
                ),
            }
        )

    def add_comment(self, ticket_key: str, comment: str) -> dict[str, Any]:
        """Add a comment to an existing ticket."""

        def run() -> dict[str, Any]:
            c = self.repo.add_comment(ticket_key, comment)
            return {"ticket": self.repo.get(ticket_key).key, "comment": comment_to_dict(c)}

        return self._safe(run)

    def update_ticket_status(
        self, ticket_key: str, status: str, note: str | None = None
    ) -> dict[str, Any]:
        """Change a ticket's status (open, in_progress, resolved, closed)."""
        return self._safe(
            lambda: {"updated": True, **ticket_to_dict(self.repo.update_status(ticket_key, status, note))}
        )

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        fn = getattr(self, name, None)
        if name not in TOOL_NAMES or fn is None:
            return {"error": f"Unknown tool: {name}"}
        try:
            result: dict[str, Any] = fn(**arguments)
            return result
        except TypeError as e:
            return {"error": f"Bad arguments for {name}: {e}"}


# OpenAI-style function schemas. The MCP server derives equivalent schemas from type hints;
# these are used by the in-process backend so both paths expose the same contract.
TICKET_TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "search_tickets",
        "description": "Search existing support tickets by keywords, status and/or requester.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Keywords to match in title/description"},
                "status": {"type": "string", "enum": STATUSES},
                "requester": {"type": "string", "description": "Username, e.g. 'paul.d'"},
                "limit": {"type": "integer", "default": 10},
            },
        },
    },
    {
        "name": "get_ticket",
        "description": "Get the details, status and comments of one ticket, e.g. 'TCK-1003'.",
        "parameters": {
            "type": "object",
            "properties": {"ticket_key": {"type": "string"}},
            "required": ["ticket_key"],
        },
    },
    {
        "name": "create_ticket",
        "description": (
            "Create a new support ticket. Only call after the user has confirmed they want one "
            "or explicitly asked for one."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Short summary of the problem"},
                "description": {"type": "string", "description": "Details, steps already tried"},
                "requester": {"type": "string", "description": "Username of the affected user"},
                "priority": {"type": "string", "enum": PRIORITIES, "default": "medium"},
                "category": {"type": "string", "default": "General"},
            },
            "required": ["title", "description", "requester"],
        },
    },
    {
        "name": "add_comment",
        "description": "Add a comment or update to an existing ticket.",
        "parameters": {
            "type": "object",
            "properties": {"ticket_key": {"type": "string"}, "comment": {"type": "string"}},
            "required": ["ticket_key", "comment"],
        },
    },
    {
        "name": "update_ticket_status",
        "description": "Change a ticket's status, e.g. reopen a resolved ticket by setting 'open'.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticket_key": {"type": "string"},
                "status": {"type": "string", "enum": STATUSES},
                "note": {"type": "string", "description": "Reason for the change"},
            },
            "required": ["ticket_key", "status"],
        },
    },
]

TOOL_NAMES = frozenset(s["name"] for s in TICKET_TOOL_SCHEMAS)
