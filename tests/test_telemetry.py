"""Unit tests for the SQLite-backed request and LLM telemetry logger."""

from __future__ import annotations

from helpdesk.telemetry import Telemetry


def test_telemetry_request_lifecycle() -> None:
    telemetry = Telemetry(":memory:")

    req_id = telemetry.start_request(
        question="How do I connect to Northwind-Guest Wi-Fi?",
        conversation_id="conv_123",
    )
    assert req_id is not None
    assert len(req_id) == 12

    # Record 2 LLM calls during this request scope
    telemetry.record_llm_call(
        model="gemini/gemini-2.5-flash",
        prompt_tokens=150,
        completion_tokens=50,
        cost_usd=0.0001,
        latency_ms=320.0,
    )
    telemetry.record_llm_call(
        model="gemini/gemini-2.5-flash",
        prompt_tokens=200,
        completion_tokens=80,
        cost_usd=0.00015,
        latency_ms=450.0,
    )

    result = telemetry.finish_request(
        request_id=req_id,
        latency_ms=800.0,
        tools_used=["get_ticket"],
        sources=["KB-003"],
    )

    assert result["request_id"] == req_id
    assert result["llm_calls"] == 2
    assert result["prompt_tokens"] == 350
    assert result["completion_tokens"] == 130
    assert result["cost_usd"] == 0.00025


def test_telemetry_summary_and_recent() -> None:
    telemetry = Telemetry(":memory:")

    # Request 1
    r1 = telemetry.start_request("Question 1")
    telemetry.record_llm_call("test-model", 100, 20, 0.001, 100.0)
    telemetry.finish_request(
        r1, latency_ms=150.0, tools_used=["search_tickets"], sources=["KB-001"]
    )

    import time

    time.sleep(0.02)

    # Request 2
    r2 = telemetry.start_request("Question 2")
    telemetry.record_llm_call("test-model", 200, 40, 0.002, 250.0)
    telemetry.finish_request(
        r2, latency_ms=300.0, tools_used=["search_tickets", "create_ticket"], sources=[]
    )

    # Summary
    summary = telemetry.summary()
    assert summary["requests"] == 2
    assert summary["errors"] == 0
    assert summary["tokens"]["prompt"] == 300
    assert summary["tokens"]["completion"] == 60
    assert summary["cost_usd"]["total"] == 0.003
    assert summary["tool_usage"]["search_tickets"] == 2
    assert summary["tool_usage"]["create_ticket"] == 1
    assert summary["latency_ms"]["avg"] == 225.0

    # Recent
    recent = telemetry.recent(limit=10)
    assert len(recent) == 2
    assert recent[0]["id"] == r2  # sorted desc by ts
