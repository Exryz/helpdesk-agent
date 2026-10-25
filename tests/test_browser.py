"""Unit tests for the portal HTML ticket scraper."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from helpdesk.browser.autofill import TicketFormDraft, build_autofill_plan
from helpdesk.browser.scraper import parse_ticket_html
from helpdesk.tickets.api import create_app
from helpdesk.tickets.repository import TicketRepository


def test_parse_ticket_html_from_portal_route() -> None:
    repo = TicketRepository.from_path(":memory:", seed=True)
    repo.add_comment("TCK-1003", "Collected AnyConnect DART bundle.", author="paul.d")
    client = TestClient(create_app(repo))

    resp = client.get("/portal/tickets/TCK-1003")
    assert resp.status_code == 200

    scraped = parse_ticket_html(resp.text)
    assert scraped.key == "TCK-1003"
    assert scraped.title == "VPN disconnects every 10 minutes"
    assert scraped.status == "open"
    assert scraped.priority == "high"
    assert scraped.category == "Network"
    assert scraped.requester == "paul.d"
    assert "AnyConnect drops" in scraped.description
    assert scraped.comments == [
        {"author": "paul.d", "body": "Collected AnyConnect DART bundle."}
    ]


def test_parse_ticket_html_rejects_invalid_markup() -> None:
    with pytest.raises(ValueError, match="valid #ticket-detail"):
        parse_ticket_html("<html><body><p>Not a ticket page</p></body></html>")


def test_build_autofill_plan_validates_and_orders_steps() -> None:
    draft = TicketFormDraft(
        title="  VPN certificate expired  ",
        requester="  paul.d ",
        priority="HIGH",
        category="Network",
        description="Error code 412 when connecting to gateway.",
    )
    plan = build_autofill_plan(draft)
    assert len(plan) == 5
    assert plan[0] == {"action": "fill", "selector": "#title", "value": "VPN certificate expired"}
    assert plan[1] == {"action": "fill", "selector": "#requester", "value": "paul.d"}
    assert plan[2] == {"action": "select_option", "selector": "#priority", "value": "high"}
    assert plan[3] == {"action": "fill", "selector": "#category", "value": "Network"}


def test_ticket_form_draft_rejects_invalid_priority() -> None:
    draft = TicketFormDraft(title="Broken dock", requester="paul.d", priority="urgent")
    with pytest.raises(ValueError, match="Invalid priority"):
        build_autofill_plan(draft)

