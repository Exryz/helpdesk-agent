"""Tests for HelpdeskAgent and ToolBackends using deterministic ScriptedLLM."""

from __future__ import annotations

import asyncio
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

import pytest

from helpdesk.agent.graph import HelpdeskAgent
from helpdesk.agent.tool_backend import LocalToolBackend, McpToolBackend
from helpdesk.config import Settings
from helpdesk.llm import LLMClient, LLMResponse, ScriptedLLM, ToolCall
from helpdesk.retrieval.hybrid import HybridRetriever
from helpdesk.telemetry import Telemetry
from helpdesk.tickets.repository import TicketRepository
from helpdesk.tickets.tools import TicketTools


@pytest.mark.asyncio
async def test_agent_kb_answer_with_citation(
    fake_retriever: HybridRetriever, local_tools: TicketTools
) -> None:
    backend = LocalToolBackend(local_tools)
    scripted_llm = ScriptedLLM([
        LLMResponse(
            content="To reset your password, visit the self-service portal [KB-004].",
            tool_calls=[],
        )
    ])
    agent = HelpdeskAgent(scripted_llm, fake_retriever, backend)

    result = await agent.run("How do I reset my password?")

    assert "[KB-004]" in result.answer
    assert [s["doc_id"] for s in result.sources] == ["KB-004"]
    assert len(result.retrieved_doc_ids) > 0
    assert result.tools_used == []
    assert result.steps == 1


@pytest.mark.asyncio
async def test_agent_sources_only_include_cited_articles(
    fake_retriever: HybridRetriever, local_tools: TicketTools
) -> None:
    scripted_llm = ScriptedLLM([LLMResponse(content="I don't know.", tool_calls=[])])
    agent = HelpdeskAgent(scripted_llm, fake_retriever, LocalToolBackend(local_tools))

    result = await agent.run("How do I reset my password?")

    assert result.sources == []
    assert len(result.retrieved_doc_ids) > 0


@pytest.mark.asyncio
async def test_agent_ticket_tool_call_flow(
    fake_retriever: HybridRetriever, repo: TicketRepository, local_tools: TicketTools
) -> None:
    backend = LocalToolBackend(local_tools)
    scripted_llm = ScriptedLLM([
        # Step 1: LLM calls get_ticket
        LLMResponse(
            content=None,
            tool_calls=[
                ToolCall(id="call_1", name="get_ticket", arguments={"ticket_key": "TCK-1003"})
            ],
        ),
        # Step 2: LLM answers using the ticket info
        LLMResponse(
            content="Ticket TCK-1003 regarding 'Teams camera not detected' is currently resolved.",
            tool_calls=[],
        ),
    ])
    agent = HelpdeskAgent(scripted_llm, fake_retriever, backend)

    result = await agent.run("Check status of TCK-1003")

    assert "TCK-1003" in result.answer
    assert "resolved" in result.answer
    assert result.tools_used == ["get_ticket"]
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0]["name"] == "get_ticket"
    assert result.tool_calls[0]["result"]["key"] == "TCK-1003"
    assert result.steps == 2


@pytest.mark.asyncio
async def test_agent_step_cap_termination(
    fake_retriever: HybridRetriever, local_tools: TicketTools
) -> None:
    backend = LocalToolBackend(local_tools)
    # Settings with max_agent_steps = 2
    settings = Settings(max_agent_steps=2)

    scripted_llm = ScriptedLLM([
        # Step 1: calls search_tickets
        LLMResponse(
            content=None,
            tool_calls=[ToolCall(id="call_1", name="search_tickets", arguments={"query": "wifi"})],
        ),
        # Step 2: capped, forces final answer
        LLMResponse(
            content="Here is what I could find before reaching the step limit.",
            tool_calls=[],
        ),
    ])
    agent = HelpdeskAgent(scripted_llm, fake_retriever, backend, settings=settings)

    result = await agent.run("Search tickets for wifi")

    assert result.steps == 2
    assert "step limit" in result.answer
    assert "search_tickets" in result.tools_used


@pytest.mark.asyncio
async def test_agent_telemetry_recording(
    fake_retriever: HybridRetriever, local_tools: TicketTools
) -> None:
    backend = LocalToolBackend(local_tools)
    telemetry = Telemetry(":memory:")
    scripted_llm = ScriptedLLM(
        [LLMResponse(content="Answer from KB [KB-001].", tool_calls=[])],
        telemetry=telemetry,
    )
    agent = HelpdeskAgent(scripted_llm, fake_retriever, backend, telemetry=telemetry)

    result = await agent.run("My question", conversation_id="conv_123")

    assert result.stats.get("request_id") is not None
    summary = telemetry.summary()
    assert summary["requests"] == 1


@pytest.mark.asyncio
async def test_mcp_tool_backend_end_to_end() -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = Path(tmpdir) / "tickets.db"
        # Seed the DB so TCK-1001 exists
        TicketRepository.from_path(db_path, seed=True)

        backend = McpToolBackend(db_path=str(db_path))
        try:
            schemas = await backend.schemas()
            assert len(schemas) == 8
            names = {s["name"] for s in schemas}
            expected_names = {
                "search_tickets",
                "get_ticket",
                "create_ticket",
                "add_comment",
                "update_ticket_status",
                "scrape_ticket_page",
                "autofill_ticket_form",
                "check_sla_breaches",
            }
            assert names == expected_names

            # Call get_ticket
            res = await backend.call("get_ticket", {"ticket_key": "TCK-1001"})
            assert res.get("key") == "TCK-1001"
            assert "Outlook" in res.get("title", "")
        finally:
            await backend.aclose()
            # Give child process a moment to release file handles on Windows
            await asyncio.sleep(0.2)


@pytest.mark.asyncio
async def test_agent_astream_events_and_done_equality(
    fake_retriever: HybridRetriever, local_tools: TicketTools
) -> None:
    backend = LocalToolBackend(local_tools)
    answer_text = "To reset your password, visit the self-service portal [KB-004]."

    # 1. Run via agent.run()
    llm1 = ScriptedLLM([LLMResponse(content=answer_text, tool_calls=[])])
    agent1 = HelpdeskAgent(llm1, fake_retriever, backend)
    run_result = await agent1.run("How do I reset my password?")

    # 2. Run via agent.astream()
    llm2 = ScriptedLLM([LLMResponse(content=answer_text, tool_calls=[])])
    agent2 = HelpdeskAgent(llm2, fake_retriever, backend)
    events: list[dict[str, Any]] = []
    async for ev in agent2.astream("How do I reset my password?"):
        events.append(ev)

    event_types = [e["type"] for e in events]
    assert event_types[0] == "retrieval"
    assert "token" in event_types
    assert event_types[-1] == "done"

    # Token deltas should reconstruct the answer
    tokens = [e["text"] for e in events if e["type"] == "token"]
    assert "".join(tokens) == answer_text

    # Done result must equal run result
    done_result = events[-1]["result"]
    assert done_result["answer"] == run_result.answer
    assert done_result["sources"] == run_result.sources
    assert done_result["tools_used"] == run_result.tools_used
    assert done_result["retrieved_doc_ids"] == run_result.retrieved_doc_ids
    assert done_result["steps"] == run_result.steps


@pytest.mark.asyncio
async def test_agent_astream_tool_call_flow(
    fake_retriever: HybridRetriever, local_tools: TicketTools
) -> None:
    backend = LocalToolBackend(local_tools)
    scripted_llm = ScriptedLLM([
        LLMResponse(
            content=None,
            tool_calls=[
                ToolCall(id="call_1", name="get_ticket", arguments={"ticket_key": "TCK-1003"})
            ],
        ),
        LLMResponse(
            content="Ticket TCK-1003 regarding 'Teams camera not detected' is currently resolved.",
            tool_calls=[],
        ),
    ])
    agent = HelpdeskAgent(scripted_llm, fake_retriever, backend)

    events: list[dict[str, Any]] = []
    async for ev in agent.astream("Check status of TCK-1003"):
        events.append(ev)

    event_types = [e["type"] for e in events]
    # Check progressive order: retrieval -> tool_call -> tool_result -> token(s) -> done
    assert event_types[0] == "retrieval"
    assert "tool_call" in event_types
    assert "tool_result" in event_types
    assert "token" in event_types
    assert event_types[-1] == "done"

    tc_idx = event_types.index("tool_call")
    tr_idx = event_types.index("tool_result")
    tok_idx = event_types.index("token")
    assert tc_idx < tr_idx < tok_idx

    tc_event = events[tc_idx]
    assert tc_event["name"] == "get_ticket"
    assert tc_event["arguments"] == {"ticket_key": "TCK-1003"}

    tr_event = events[tr_idx]
    assert tr_event["name"] == "get_ticket"
    assert tr_event["result"]["key"] == "TCK-1003"

    done_res = events[-1]["result"]
    assert "TCK-1003" in done_res["answer"]
    assert done_res["tools_used"] == ["get_ticket"]


@pytest.mark.asyncio
async def test_agent_astream_fallback_when_llm_lacks_chat_stream(
    fake_retriever: HybridRetriever, local_tools: TicketTools
) -> None:
    backend = LocalToolBackend(local_tools)

    class NoStreamLLM:
        def __init__(self, content: str) -> None:
            self.content = content
            self.calls: list[Any] = []

        async def chat(
            self,
            messages: Sequence[dict[str, Any]],
            tools: Sequence[dict[str, Any]] | None = None,
            temperature: float | None = None,
            json_mode: bool = False,
        ) -> LLMResponse:
            self.calls.append(messages)
            return LLMResponse(content=self.content, tool_calls=[])

    raw_llm = NoStreamLLM("Fallback answer citing [KB-004].")
    assert not hasattr(raw_llm, "chat_stream")
    agent = HelpdeskAgent(cast(LLMClient, raw_llm), fake_retriever, backend)

    events: list[dict[str, Any]] = []
    async for ev in agent.astream("How do I reset my password?"):
        events.append(ev)

    event_types = [e["type"] for e in events]
    assert "retrieval" in event_types
    assert "token" in event_types
    assert event_types[-1] == "done"

    done_res = events[-1]["result"]
    assert "Fallback answer" in done_res["answer"]
    assert [s["doc_id"] for s in done_res["sources"]] == ["KB-004"]

