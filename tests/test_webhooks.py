"""Unit and security tests for Slack and Microsoft Teams webhooks."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from fastapi.testclient import TestClient

from helpdesk.agent.graph import HelpdeskAgent
from helpdesk.agent.tool_backend import LocalToolBackend
from helpdesk.api.main import create_app
from helpdesk.config import Settings
from helpdesk.llm import LLMResponse, ScriptedLLM
from helpdesk.retrieval.hybrid import HybridRetriever
from helpdesk.telemetry import Telemetry
from helpdesk.tickets.repository import TicketRepository
from helpdesk.tickets.tools import TicketTools


def _make_slack_headers(secret: str, raw_body: bytes, timestamp: int | None = None) -> dict[str, str]:
    ts = int(time.time()) if timestamp is None else timestamp
    basestring = f"v0:{ts}:".encode() + raw_body
    sig = "v0=" + hmac.new(secret.encode(), basestring, hashlib.sha256).hexdigest()
    return {"X-Slack-Request-Timestamp": str(ts), "X-Slack-Signature": sig}


def _make_teams_headers(secret_b64: str, raw_body: bytes) -> dict[str, str]:
    decoded_key = base64.b64decode(secret_b64)
    digest = hmac.new(decoded_key, raw_body, hashlib.sha256).digest()
    sig_b64 = base64.b64encode(digest).decode()
    return {"Authorization": f"HMAC {sig_b64}"}


def _build_test_client(
    fake_retriever: HybridRetriever,
    repo: TicketRepository,
    local_tools: TicketTools,
    settings: Settings,
    responses: list[LLMResponse] | None = None,
) -> tuple[TestClient, ScriptedLLM]:
    telemetry = Telemetry(":memory:")
    backend = LocalToolBackend(local_tools)
    scripted_llm = ScriptedLLM(
        responses or [LLMResponse(content="Helpdesk webhook answer.", tool_calls=[])],
        telemetry=telemetry,
    )
    agent = HelpdeskAgent(scripted_llm, fake_retriever, backend, settings=settings, telemetry=telemetry)
    app = create_app(agent=agent, telemetry=telemetry, repo=repo, settings=settings)
    return TestClient(app), scripted_llm


def test_slack_valid_signature_json(
    fake_retriever: HybridRetriever, repo: TicketRepository, local_tools: TicketTools
) -> None:
    settings = Settings(slack_signing_secret="slack_secret_key_123")
    client, _ = _build_test_client(fake_retriever, repo, local_tools, settings)

    raw_body = json.dumps({"text": "Reset password request", "channel_id": "C01TECH"}).encode()
    headers = _make_slack_headers("slack_secret_key_123", raw_body)
    headers["Content-Type"] = "application/json"

    resp = client.post("/webhooks/slack", content=raw_body, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "Helpdesk webhook answer" in data["text"]
    assert data["conversation_id"] == "slack:C01TECH"


def test_slack_invalid_signature_fails_with_401(
    fake_retriever: HybridRetriever, repo: TicketRepository, local_tools: TicketTools
) -> None:
    settings = Settings(slack_signing_secret="slack_secret_key_123")
    client, _ = _build_test_client(fake_retriever, repo, local_tools, settings)

    raw_body = json.dumps({"text": "Reset password request", "channel_id": "C01TECH"}).encode()
    headers = {
        "X-Slack-Request-Timestamp": str(int(time.time())),
        "X-Slack-Signature": "v0=bad_signature_hex",
        "Content-Type": "application/json",
    }

    resp = client.post("/webhooks/slack", content=raw_body, headers=headers)
    assert resp.status_code == 401


def test_slack_stale_timestamp_fails_with_401(
    fake_retriever: HybridRetriever, repo: TicketRepository, local_tools: TicketTools
) -> None:
    settings = Settings(slack_signing_secret="slack_secret_key_123")
    client, _ = _build_test_client(fake_retriever, repo, local_tools, settings)

    raw_body = json.dumps({"text": "Old message"}).encode()
    stale_ts = int(time.time()) - 400
    headers = _make_slack_headers("slack_secret_key_123", raw_body, timestamp=stale_ts)
    headers["Content-Type"] = "application/json"

    resp = client.post("/webhooks/slack", content=raw_body, headers=headers)
    assert resp.status_code == 401


def test_slack_slash_command_form_payload(
    fake_retriever: HybridRetriever, repo: TicketRepository, local_tools: TicketTools
) -> None:
    settings = Settings(slack_signing_secret="slack_secret_key_123")
    client, _ = _build_test_client(fake_retriever, repo, local_tools, settings)

    form_body = b"command=%2Fhelpdesk&text=Need+wifi+access&channel_id=C999&user_id=U123"
    headers = _make_slack_headers("slack_secret_key_123", form_body)
    headers["Content-Type"] = "application/x-www-form-urlencoded"

    resp = client.post("/webhooks/slack", content=form_body, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["conversation_id"] == "slack:C999"
    assert "Helpdesk webhook answer" in data["text"]


def test_slack_bot_id_event_ignored(
    fake_retriever: HybridRetriever, repo: TicketRepository, local_tools: TicketTools
) -> None:
    settings = Settings(slack_signing_secret="slack_secret_key_123")
    client, scripted_llm = _build_test_client(fake_retriever, repo, local_tools, settings)

    bot_payload = {
        "type": "event_callback",
        "event": {
            "type": "message",
            "text": "automated bot echo",
            "bot_id": "B012345678",
            "channel": "C01TECH",
        },
    }
    raw_body = json.dumps(bot_payload).encode()
    headers = _make_slack_headers("slack_secret_key_123", raw_body)
    headers["Content-Type"] = "application/json"

    resp = client.post("/webhooks/slack", content=raw_body, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ignored"
    # Agent was never called
    assert len(scripted_llm.calls) == 0


def test_teams_valid_hmac(
    fake_retriever: HybridRetriever, repo: TicketRepository, local_tools: TicketTools
) -> None:
    teams_secret_b64 = base64.b64encode(b"my_teams_secret_key_32_bytes_long!").decode()
    settings = Settings(teams_webhook_secret=teams_secret_b64)
    client, _ = _build_test_client(fake_retriever, repo, local_tools, settings)

    payload = {
        "type": "message",
        "text": "<at>ITBot</at> VPN connection failed on Windows",
        "conversation": {"id": "19:conv_teams_99"},
    }
    raw_body = json.dumps(payload).encode()
    headers = _make_teams_headers(teams_secret_b64, raw_body)
    headers["Content-Type"] = "application/json"

    resp = client.post("/webhooks/teams", content=raw_body, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "message"
    assert data["conversation_id"] == "teams:19:conv_teams_99"


def test_teams_invalid_hmac_fails_with_401(
    fake_retriever: HybridRetriever, repo: TicketRepository, local_tools: TicketTools
) -> None:
    teams_secret_b64 = base64.b64encode(b"my_teams_secret_key_32_bytes_long!").decode()
    settings = Settings(teams_webhook_secret=teams_secret_b64)
    client, _ = _build_test_client(fake_retriever, repo, local_tools, settings)

    raw_body = json.dumps({"text": "Hello"}).encode()
    headers = {"Authorization": "HMAC bad_hmac_string", "Content-Type": "application/json"}

    resp = client.post("/webhooks/teams", content=raw_body, headers=headers)
    assert resp.status_code == 401


def test_webhooks_dev_mode_without_secrets(
    fake_retriever: HybridRetriever, repo: TicketRepository, local_tools: TicketTools
) -> None:
    settings = Settings(slack_signing_secret=None, teams_webhook_secret=None)
    client, _ = _build_test_client(
        fake_retriever,
        repo,
        local_tools,
        settings,
        responses=[
            LLMResponse(content="Dev mode slack answer", tool_calls=[]),
            LLMResponse(content="Dev mode teams answer", tool_calls=[]),
        ],
    )

    # Slack without any signature headers in dev mode succeeds
    slack_resp = client.post(
        "/webhooks/slack",
        json={"text": "Dev mode slack test", "channel_id": "C_DEV"},
    )
    assert slack_resp.status_code == 200
    assert slack_resp.json()["conversation_id"] == "slack:C_DEV"

    # Teams without Authorization header in dev mode succeeds
    teams_resp = client.post(
        "/webhooks/teams",
        json={"text": "Dev mode teams test", "conversation": {"id": "conv_dev"}},
    )
    assert teams_resp.status_code == 200
    assert teams_resp.json()["conversation_id"] == "teams:conv_dev"
