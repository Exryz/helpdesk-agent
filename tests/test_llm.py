"""Unit tests for LLM streaming and ScriptedLLM behavior."""

from __future__ import annotations

import pytest

from helpdesk.llm import LLMResponse, ScriptedLLM, StreamEvent, ToolCall
from helpdesk.telemetry import Telemetry


def test_stream_event_dataclass() -> None:
    delta_ev = StreamEvent(kind="delta", text="chunk")
    assert delta_ev.kind == "delta"
    assert delta_ev.text == "chunk"
    assert delta_ev.response is None

    resp = LLMResponse(content="Full response", tool_calls=[])
    resp_ev = StreamEvent(kind="response", response=resp)
    assert resp_ev.kind == "response"
    assert resp_ev.response == resp
    assert resp_ev.text == ""


@pytest.mark.asyncio
async def test_scripted_llm_chat_stream_text() -> None:
    telemetry = Telemetry(":memory:")
    scripted_llm = ScriptedLLM(
        [
            LLMResponse(
                content="Hello world from helpdesk assistant",
                tool_calls=[],
                prompt_tokens=10,
                completion_tokens=5,
                cost_usd=0.001,
            )
        ],
        telemetry=telemetry,
    )

    events: list[StreamEvent] = []
    async for ev in scripted_llm.chat_stream([{"role": "user", "content": "hi"}]):
        events.append(ev)

    deltas = [e.text for e in events if e.kind == "delta"]
    assert "".join(deltas) == "Hello world from helpdesk assistant"
    assert len(deltas) == 5

    responses = [e.response for e in events if e.kind == "response"]
    assert len(responses) == 1
    assert responses[0] is not None
    assert responses[0].content == "Hello world from helpdesk assistant"

    # Telemetry should be recorded
    with telemetry._lock:
        count = telemetry._conn.execute("SELECT count(*) FROM llm_calls").fetchone()[0]
    assert count == 1


@pytest.mark.asyncio
async def test_scripted_llm_chat_stream_tool_call_turn() -> None:
    scripted_llm = ScriptedLLM([
        LLMResponse(
            content=None,
            tool_calls=[ToolCall(id="c1", name="get_ticket", arguments={"ticket_key": "TCK-1001"})],
        )
    ])

    events: list[StreamEvent] = []
    async for ev in scripted_llm.chat_stream([{"role": "user", "content": "get ticket"}]):
        events.append(ev)

    deltas = [e for e in events if e.kind == "delta"]
    assert len(deltas) == 0

    responses = [e.response for e in events if e.kind == "response"]
    assert len(responses) == 1
    assert responses[0] is not None
    assert len(responses[0].tool_calls) == 1
    assert responses[0].tool_calls[0].name == "get_ticket"
