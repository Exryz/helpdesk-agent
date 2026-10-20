"""Tests for FastAPI endpoints (/health, /chat, /metrics, /tickets)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from helpdesk.agent.graph import HelpdeskAgent
from helpdesk.agent.tool_backend import LocalToolBackend
from helpdesk.api.main import create_app
from helpdesk.llm import LLMResponse, ScriptedLLM
from helpdesk.retrieval.hybrid import HybridRetriever
from helpdesk.telemetry import Telemetry
from helpdesk.tickets.repository import TicketRepository
from helpdesk.tickets.tools import TicketTools


@pytest.fixture
def app_and_client(
    fake_retriever: HybridRetriever, repo: TicketRepository, local_tools: TicketTools
):
    telemetry = Telemetry(":memory:")
    backend = LocalToolBackend(local_tools)

    scripted_llm = ScriptedLLM(
        [
            LLMResponse(content="First response citing [KB-004].", tool_calls=[]),
            LLMResponse(content="Second response in conversation.", tool_calls=[]),
        ],
        telemetry=telemetry,
    )
    agent = HelpdeskAgent(scripted_llm, fake_retriever, backend, telemetry=telemetry)
    app = create_app(agent=agent, telemetry=telemetry, repo=repo)

    with TestClient(app) as client:
        yield client, scripted_llm


def test_health_endpoint(app_and_client) -> None:
    client, _ = app_and_client
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_chat_endpoint_single_turn(app_and_client) -> None:
    client, _ = app_and_client
    payload = {"message": "How do I reset my password?"}
    resp = client.post("/chat", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "First response" in data["answer"]
    assert len(data["sources"]) > 0
    assert data["conversation_id"] is not None
    assert isinstance(data["stats"], dict)


def test_chat_multi_turn_history(app_and_client) -> None:
    client, scripted_llm = app_and_client
    # Turn 1
    resp1 = client.post("/chat", json={"message": "First message"})
    assert resp1.status_code == 200
    cid = resp1.json()["conversation_id"]

    # Turn 2 using same conversation_id
    resp2 = client.post("/chat", json={"message": "Second message", "conversation_id": cid})
    assert resp2.status_code == 200
    assert "Second response" in resp2.json()["answer"]

    # Check that the second call to LLM included conversation history
    # scripted_llm.calls records the messages sent to the LLM on each call
    assert len(scripted_llm.calls) == 2
    second_call_msgs = scripted_llm.calls[1]
    # Verify that the first user message and first assistant response are in history
    roles = [m.get("role") for m in second_call_msgs]
    contents = [m.get("content", "") for m in second_call_msgs]
    assert "user" in roles
    assert any("First message" in c for c in contents)
    assert any("First response" in c for c in contents)


def test_metrics_endpoints(app_and_client) -> None:
    client, _ = app_and_client
    client.post("/chat", json={"message": "Ping metrics"})

    resp_summary = client.get("/metrics")
    assert resp_summary.status_code == 200
    summary = resp_summary.json()
    assert summary["requests"] >= 1

    resp_recent = client.get("/metrics/recent?limit=5")
    assert resp_recent.status_code == 200
    recent = resp_recent.json()
    assert len(recent) >= 1
    assert recent[0]["question"] == "Ping metrics"


def test_mounted_tickets_routes(app_and_client) -> None:
    client, _ = app_and_client
    # List tickets
    resp_list = client.get("/tickets")
    assert resp_list.status_code == 200
    tickets = resp_list.json()
    assert len(tickets) > 0

    # Get single ticket
    resp_ticket = client.get("/tickets/TCK-1001")
    assert resp_ticket.status_code == 200
    ticket = resp_ticket.json()
    assert ticket["key"] == "TCK-1001"
    assert "Outlook" in ticket["title"]
