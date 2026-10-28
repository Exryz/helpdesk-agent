"""Unit tests for the portal HTML ticket scraper."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from helpdesk.agent import HelpdeskAgent, LocalToolBackend, McpToolBackend
from helpdesk.browser.autofill import (
    TicketFormDraft,
    build_autofill_plan,
    extract_screenshot_paths,
)
from helpdesk.browser.scraper import parse_ticket_html
from helpdesk.llm import LLMResponse, ScriptedLLM, ToolCall
from helpdesk.retrieval.hybrid import HybridRetriever
from helpdesk.tickets.api import create_app
from helpdesk.tickets.repository import TicketRepository
from helpdesk.tickets.tools import TicketTools


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


def test_browser_tools_via_ticket_tools_dispatch() -> None:
    repo = TicketRepository.from_path(":memory:", seed=True)
    tools = TicketTools(repo)
    client = TestClient(create_app(repo))

    html_doc = client.get("/portal/tickets/TCK-1001").text
    scraped = tools.call("scrape_ticket_page", {"html": html_doc})
    assert scraped["key"] == "TCK-1001"
    assert scraped["requester"] == "maria.santos"

    autofill = tools.call(
        "autofill_ticket_form",
        {
            "title": scraped["title"],
            "requester": scraped["requester"],
            "priority": scraped["priority"],
            "category": scraped["category"],
            "description": scraped["description"],
        },
    )
    assert autofill["filled"] is False
    assert autofill["fields"]["title"] == "Outlook not syncing on laptop"
    assert len(autofill["plan"]) == 5


def test_browser_tools_return_error_dicts_on_bad_input() -> None:
    repo = TicketRepository.from_path(":memory:", seed=True)
    tools = TicketTools(repo)

    missing_arg = tools.call("scrape_ticket_page", {})
    assert "error" in missing_arg

    bad_prio = tools.call(
        "autofill_ticket_form",
        {"title": "Dock issue", "requester": "paul.d", "priority": "invalid_prio"},
    )
    assert "error" in bad_prio


@pytest.mark.asyncio
async def test_agent_chains_scrape_and_autofill_tools(
    fake_retriever: HybridRetriever, repo: TicketRepository, local_tools: TicketTools
) -> None:
    client = TestClient(create_app(repo))
    portal_html = client.get("/portal/tickets/TCK-1003").text

    scripted_llm = ScriptedLLM(
        [
            LLMResponse(
                content="",
                tool_calls=[
                    ToolCall(
                        id="call_scrape_1",
                        name="scrape_ticket_page",
                        arguments={"html": portal_html},
                    )
                ],
            ),
            LLMResponse(
                content="",
                tool_calls=[
                    ToolCall(
                        id="call_autofill_2",
                        name="autofill_ticket_form",
                        arguments={
                            "title": "Follow-up: VPN disconnects every 10 minutes",
                            "requester": "paul.d",
                            "priority": "high",
                            "category": "Network",
                            "description": "Escalating from TCK-1003 with AnyConnect DART logs.",
                        },
                    )
                ],
            ),
            LLMResponse(
                content=(
                    "I scraped TCK-1003 and pre-filled the follow-up ticket form for paul.d "
                    "(High priority, Network). Would you like me to submit it?"
                ),
                tool_calls=[],
            ),
        ]
    )

    agent = HelpdeskAgent(scripted_llm, fake_retriever, LocalToolBackend(local_tools))
    result = await agent.run("Scrape TCK-1003 from the portal and pre-fill a follow-up ticket form.")

    assert result.tools_used == ["scrape_ticket_page", "autofill_ticket_form"]
    assert len(result.tool_calls) == 2
    assert result.tool_calls[0]["result"]["key"] == "TCK-1003"
    assert result.tool_calls[1]["result"]["fields"]["requester"] == "paul.d"
    assert "pre-filled" in result.answer


@pytest.mark.asyncio
async def test_mcp_backend_executes_browser_tools_over_stdio() -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = Path(tmpdir) / "tickets.db"
        repo = TicketRepository.from_path(db_path, seed=True)
        html_doc = TestClient(create_app(repo)).get("/portal/tickets/TCK-1002").text
        repo.engine.dispose()

        backend = McpToolBackend(db_path=str(db_path))
        try:
            scraped = await backend.call("scrape_ticket_page", {"html": html_doc})
            assert scraped.get("key") == "TCK-1002"
            assert scraped.get("requester") == "john.reyes"

            autofill = await backend.call(
                "autofill_ticket_form",
                {
                    "title": str(scraped["title"]),
                    "requester": str(scraped["requester"]),
                    "priority": "medium",
                    "category": "Accounts & Access",
                },
            )
            assert autofill.get("filled") is False
            assert len(autofill.get("plan", [])) == 5
        finally:
            await backend.aclose()
            await asyncio.sleep(0.2)


def test_extract_screenshot_paths_filters_existing_files(tmp_path: Path) -> None:
    shot = tmp_path / "preview.png"
    shot.write_bytes(b"\x89PNG\r\n\x1a\n")

    tool_calls = [
        {"name": "scrape_ticket_page", "result": {"key": "TCK-1001"}},
        {"name": "autofill_ticket_form", "result": {"screenshot_path": str(shot)}},
        {"name": "autofill_ticket_form", "result": {"screenshot_path": str(tmp_path / "missing.png")}},
    ]
    assert extract_screenshot_paths(tool_calls) == [str(shot)]




