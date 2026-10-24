"""Unit and API integration tests for the mock ticketing system."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from helpdesk.tickets.api import create_app
from helpdesk.tickets.repository import (
    Priority,
    Status,
    TicketNotFound,
    TicketRepository,
)
from helpdesk.tickets.tools import TOOL_NAMES, TicketTools


def test_repository_crud() -> None:
    repo = TicketRepository.from_path(":memory:", seed=False)

    # Create ticket
    ticket = repo.create(
        title="Cannot connect to Outlook",
        description="Getting disconnected message on desktop client",
        requester="alice.smith",
        priority=Priority.HIGH,
        category="Email",
    )
    assert ticket.key == "TCK-1001"
    assert ticket.status == Status.OPEN.value
    assert ticket.priority == Priority.HIGH.value

    # Get ticket
    fetched = repo.get("TCK-1001")
    assert fetched.key == ticket.key
    assert fetched.requester == "alice.smith"

    # Add comments
    c1 = repo.add_comment("TCK-1001", "Tried rebooting, still failing", author="alice.smith")
    assert c1.ticket_id == 1001
    assert c1.body == "Tried rebooting, still failing"

    comments = repo.comments("TCK-1001")
    assert len(comments) == 1
    assert comments[0].id == c1.id

    # Update status
    updated = repo.update_status("TCK-1001", Status.RESOLVED, note="Fixed DNS profile")
    assert updated.status == Status.RESOLVED.value

    # Status change comment recorded
    comments_after = repo.comments("TCK-1001")
    assert len(comments_after) == 2

    # Not found raises TicketNotFound
    with pytest.raises(TicketNotFound):
        repo.get("TCK-9999")


def test_repository_search() -> None:
    repo = TicketRepository.from_path(":memory:", seed=True)

    # Search by status
    in_prog = repo.search(status=Status.IN_PROGRESS.value)
    assert len(in_prog) > 0
    assert all(t.status == Status.IN_PROGRESS.value for t in in_prog)

    # Search by query
    vpn_tickets = repo.search(query="VPN")
    assert len(vpn_tickets) > 0
    assert any("VPN" in t.title or "VPN" in t.description for t in vpn_tickets)

    # Search by requester
    user_tickets = repo.search(requester="paul.d")
    assert len(user_tickets) > 0
    assert all(t.requester == "paul.d" for t in user_tickets)


def test_ticket_tools() -> None:
    repo = TicketRepository.from_path(":memory:", seed=True)
    tools = TicketTools(repo)

    # Test TOOL_NAMES
    assert "search_tickets" in TOOL_NAMES
    assert "get_ticket" in TOOL_NAMES
    assert "create_ticket" in TOOL_NAMES
    assert "add_comment" in TOOL_NAMES
    assert "update_ticket_status" in TOOL_NAMES

    # Successful call via dispatch
    res = tools.call("get_ticket", {"ticket_key": "TCK-1001"})
    assert "error" not in res
    assert res["key"] == "TCK-1001"
    assert "comments" in res

    # Unknown ticket returns error dict (does not raise)
    err_res = tools.call("get_ticket", {"ticket_key": "TCK-9999"})
    assert "error" in err_res

    # Unknown tool returns error dict
    unknown_res = tools.call("non_existent_tool", {})
    assert "error" in unknown_res
    assert "Unknown tool" in unknown_res["error"]

    # Bad arguments return error dict
    bad_args_res = tools.call("add_comment", {"invalid_param": 123})
    assert "error" in bad_args_res

    # Create ticket via tool
    created = tools.create_ticket(
        title="Dock monitor flickering",
        description="Dell WD19 dock loses sync with external display",
        requester="bob.dylan",
    )
    assert created.get("created") is True
    assert "key" in created


def test_ticket_api_routes() -> None:
    repo = TicketRepository.from_path(":memory:", seed=True)
    app = create_app(repo)
    client = TestClient(app)

    # GET /tickets
    res = client.get("/tickets?status=open")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) > 0

    # GET /tickets/{key}
    res_get = client.get("/tickets/TCK-1001")
    assert res_get.status_code == 200
    assert res_get.json()["key"] == "TCK-1001"

    # GET /tickets/unknown returns 404
    res_404 = client.get("/tickets/TCK-9999")
    assert res_404.status_code == 404

    # POST /tickets
    create_payload = {
        "title": "Need Visio license",
        "description": "Architecture diagramming for Q3",
        "requester": "engineer.joe",
        "priority": "low",
        "category": "Software",
    }
    res_post = client.post("/tickets", json=create_payload)
    assert res_post.status_code == 201
    new_ticket = res_post.json()
    new_key = new_ticket["key"]
    assert new_ticket["requester"] == "engineer.joe"

    # POST /tickets/{key}/comments
    comment_payload = {"body": "Manager approved purchase order.", "author": "manager.jane"}
    res_comm = client.post(f"/tickets/{new_key}/comments", json=comment_payload)
    assert res_comm.status_code == 201
    assert res_comm.json()["body"] == "Manager approved purchase order."

    # PATCH /tickets/{key}/status
    patch_payload = {"status": "in_progress", "note": "Procurement requested quote"}
    res_patch = client.patch(f"/tickets/{new_key}/status", json=patch_payload)
    assert res_patch.status_code == 200
    assert res_patch.json()["status"] == "in_progress"

    # GET /portal/tickets/{key} and /portal/new (HTML portal pages)
    res_portal = client.get(f"/portal/tickets/{new_key}")
    assert res_portal.status_code == 200
    assert 'data-field="title">Need Visio license</h1>' in res_portal.text
    assert 'data-field="requester">engineer.joe</dd>' in res_portal.text

    res_form = client.get("/portal/new")
    assert res_form.status_code == 200
    assert '<form id="ticket-form"' in res_form.text
