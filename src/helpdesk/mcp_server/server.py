"""MCP server exposing the ticket tools over stdio.

Works with any MCP-compatible client (this project's agent, VS Code, etc.):

    python -m helpdesk.mcp_server.server
"""

from __future__ import annotations

import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from helpdesk.config import get_settings
from helpdesk.tickets.repository import TicketRepository
from helpdesk.tickets.tools import TicketTools


def build_server(tools: TicketTools) -> FastMCP:
    mcp = FastMCP("helpdesk-tickets")

    @mcp.tool()
    def search_tickets(
        query: str | None = None,
        status: str | None = None,
        requester: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Search existing support tickets by keywords, status
        (open, in_progress, resolved, closed) and/or requester username."""
        return tools.search_tickets(query, status, requester, limit)

    @mcp.tool()
    def get_ticket(ticket_key: str) -> dict[str, Any]:
        """Get the details, status and comments of one ticket, e.g. 'TCK-1003'."""
        return tools.get_ticket(ticket_key)

    @mcp.tool()
    def create_ticket(
        title: str,
        description: str,
        requester: str,
        priority: str = "medium",
        category: str = "General",
    ) -> dict[str, Any]:
        """Create a new support ticket (priority: low, medium, high, critical).
        Only call after the user has confirmed they want one or explicitly asked for one."""
        return tools.create_ticket(title, description, requester, priority, category)

    @mcp.tool()
    def add_comment(ticket_key: str, comment: str) -> dict[str, Any]:
        """Add a comment or update to an existing ticket."""
        return tools.add_comment(ticket_key, comment)

    @mcp.tool()
    def update_ticket_status(
        ticket_key: str, status: str, note: str | None = None
    ) -> dict[str, Any]:
        """Change a ticket's status (open, in_progress, resolved, closed),
        e.g. reopen a resolved ticket by setting 'open'."""
        return tools.update_ticket_status(ticket_key, status, note)

    return mcp


def main() -> None:
    db = os.environ.get("HELPDESK_TICKETS_DB") or str(get_settings().tickets_db)
    build_server(TicketTools(TicketRepository.from_path(db))).run(transport="stdio")


if __name__ == "__main__":
    main()
