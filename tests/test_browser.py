"""Unit tests for the portal HTML ticket scraper."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

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
