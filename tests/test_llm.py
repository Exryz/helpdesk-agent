"""Unit tests for the LLM abstraction and ScriptedLLM fake."""

from __future__ import annotations

import pytest

from helpdesk.llm import LLMResponse, ScriptedLLM, ToolCall, _parse_args
from helpdesk.telemetry import Telemetry


def test_tool_call_to_openai() -> None:
    tc = ToolCall(id="call_1", name="search_tickets", arguments={"query": "VPN"})
    payload = tc.to_openai()

    assert payload["id"] == "call_1"
    assert payload["type"] == "function"
    assert payload["function"]["name"] == "search_tickets"
    assert '"query": "VPN"' in payload["function"]["arguments"]


def test_llm_response_as_message() -> None:
    # Text-only response
    resp = LLMResponse(content="Here is the troubleshooting guide.", tool_calls=[])
    msg = resp.as_message()
    assert msg["role"] == "assistant"
    assert msg["content"] == "Here is the troubleshooting guide."
    assert "tool_calls" not in msg

    # Response with tool calls
    tc = ToolCall(id="call_99", name="get_ticket", arguments={"ticket_key": "TCK-1001"})
    resp_tc = LLMResponse(content=None, tool_calls=[tc])
    msg_tc = resp_tc.as_message()
    assert msg_tc["role"] == "assistant"
    assert msg_tc["content"] == ""
    assert len(msg_tc["tool_calls"]) == 1
    assert msg_tc["tool_calls"][0]["function"]["name"] == "get_ticket"


def test_parse_args_helper() -> None:
    # Dictionary passes through
    assert _parse_args({"foo": "bar"}) == {"foo": "bar"}

    # JSON string
    assert _parse_args('{"limit": 5}') == {"limit": 5}

    # Empty / None
    assert _parse_args("") == {}
    assert _parse_args(None) == {}

    # Invalid JSON
    assert _parse_args("invalid json {") == {}


@pytest.mark.asyncio
async def test_scripted_llm_list_mode() -> None:
    telemetry = Telemetry(":memory:")
    responses = [
        LLMResponse(content="Response 1", prompt_tokens=10, completion_tokens=5, cost_usd=0.0001),
        LLMResponse(content="Response 2", prompt_tokens=20, completion_tokens=10, cost_usd=0.0002),
    ]

    llm = ScriptedLLM(script=responses, telemetry=telemetry)

    r1 = await llm.chat([{"role": "user", "content": "Hello"}])
    assert r1.content == "Response 1"

    r2 = await llm.chat([{"role": "user", "content": "Next"}])
    assert r2.content == "Response 2"

    assert len(llm.calls) == 2
    assert llm.calls[0][0]["content"] == "Hello"

    # Out of responses raises RuntimeError
    with pytest.raises(RuntimeError, match="ran out of responses"):
        await llm.chat([{"role": "user", "content": "Another"}])


@pytest.mark.asyncio
async def test_scripted_llm_callable_mode() -> None:
    def responder(messages, tools):
        user_msg = messages[-1]["content"]
        return LLMResponse(content=f"Echo: {user_msg}")

    llm = ScriptedLLM(script=responder)
    res = await llm.chat([{"role": "user", "content": "Testing callable"}])
    assert res.content == "Echo: Testing callable"
