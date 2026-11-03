"""Slack and Microsoft Teams webhook adapters for the helpdesk agent."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import time
import urllib.parse
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException, Request
from pydantic import BaseModel

from helpdesk.agent import HelpdeskAgent
from helpdesk.config import Settings, get_settings

_TEAMS_MENTION_RE = re.compile(r"<at>.*?</at>", re.IGNORECASE | re.DOTALL)


def strip_teams_mentions(text: str) -> str:
    """Remove `<at>BotName</at>` mention tags from a Microsoft Teams webhook message."""
    return _TEAMS_MENTION_RE.sub("", text).strip()


class SlackWebhookPayload(BaseModel):
    type: str | None = None
    challenge: str | None = None
    text: str | None = None
    channel_id: str | None = None
    user_id: str | None = None
    event: dict[str, Any] | None = None


class TeamsWebhookPayload(BaseModel):
    text: str = ""
    conversation: dict[str, Any] | None = None


def _get_settings(app: FastAPI, request: Request | None = None) -> Settings:
    if request is not None and hasattr(request.app.state, "settings"):
        s: Settings | None = getattr(request.app.state, "settings", None)
        if s is not None:
            return s
    if hasattr(app.state, "settings"):
        s = getattr(app.state, "settings", None)
        if s is not None:
            return s
    return get_settings()


def _verify_slack_signature(request: Request, raw_body: bytes, secret: str) -> None:
    timestamp = request.headers.get("X-Slack-Request-Timestamp")
    signature = request.headers.get("X-Slack-Signature")
    if not timestamp or not signature:
        raise HTTPException(status_code=401, detail="Missing Slack signature or timestamp")

    try:
        ts = int(timestamp)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid Slack timestamp") from None

    if abs(time.time() - ts) > 300:
        raise HTTPException(status_code=401, detail="Slack request timestamp is stale")

    basestring = f"v0:{timestamp}:".encode() + raw_body
    expected_sig = "v0=" + hmac.new(secret.encode(), basestring, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_sig, signature):
        raise HTTPException(status_code=401, detail="Invalid Slack signature")


def _verify_teams_hmac(request: Request, raw_body: bytes, secret: str) -> None:
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing Teams Authorization header")

    parts = auth_header.split(" ", 1)
    if len(parts) != 2 or parts[0] != "HMAC":
        raise HTTPException(status_code=401, detail="Invalid Teams Authorization header format")

    received_mac = parts[1].strip()

    try:
        decoded_secret = base64.b64decode(secret)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Teams secret configuration") from None

    computed_mac = base64.b64encode(
        hmac.new(decoded_secret, raw_body, hashlib.sha256).digest()
    ).decode("utf-8")

    if not hmac.compare_digest(received_mac, computed_mac):
        raise HTTPException(status_code=401, detail="Invalid Teams webhook HMAC signature")


def build_webhook_router(app: FastAPI) -> APIRouter:
    router = APIRouter(prefix="/webhooks", tags=["webhooks"])

    @router.post("/slack")
    async def slack_webhook(request: Request) -> dict[str, Any]:
        settings = _get_settings(app, request)
        raw_body = await request.body()

        if settings.slack_signing_secret:
            _verify_slack_signature(request, raw_body, settings.slack_signing_secret)

        content_type = request.headers.get("content-type", "").lower()
        if "application/x-www-form-urlencoded" in content_type:
            parsed = urllib.parse.parse_qs(raw_body.decode("utf-8"))
            question = (parsed.get("text", [""])[0]).strip()
            channel = parsed.get("channel_id", ["default"])[0]
        else:
            try:
                data = json.loads(raw_body.decode("utf-8"))
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid JSON body") from None

            if data.get("type") == "url_verification":
                return {"challenge": data.get("challenge")}

            event = data.get("event") or {}
            if event.get("bot_id") or data.get("bot_id"):
                return {"status": "ignored", "reason": "bot_event"}

            question = (event.get("text") or data.get("text") or "").strip()
            channel = str(event.get("channel") or data.get("channel_id") or "default")

        if not question:
            raise HTTPException(status_code=400, detail="Missing message text in Slack payload")

        cid = f"slack:{channel}"
        current_agent: HelpdeskAgent = app.state.agent
        history = app.state.telemetry.get_history(cid, limit=20)
        result = await current_agent.run(question=question, history=history, conversation_id=cid)
        app.state.telemetry.append_turn(cid, question, result.answer, max_messages=20)

        return {
            "response_type": "in_channel",
            "text": result.answer,
            "blocks": [
                {"type": "section", "text": {"type": "mrkdwn", "text": result.answer}},
            ],
            "sources": result.sources,
            "tools_used": result.tools_used,
            "conversation_id": cid,
        }

    @router.post("/teams")
    async def teams_webhook(request: Request) -> dict[str, Any]:
        settings = _get_settings(app, request)
        raw_body = await request.body()

        if settings.teams_webhook_secret:
            _verify_teams_hmac(request, raw_body, settings.teams_webhook_secret)

        try:
            data = json.loads(raw_body.decode("utf-8"))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON body") from None

        question = strip_teams_mentions(str(data.get("text") or ""))
        if not question:
            raise HTTPException(status_code=400, detail="Missing message text in Teams payload")

        conv_id = str((data.get("conversation") or {}).get("id") or "default")
        cid = f"teams:{conv_id}"
        current_agent: HelpdeskAgent = app.state.agent
        history = app.state.telemetry.get_history(cid, limit=20)
        result = await current_agent.run(question=question, history=history, conversation_id=cid)
        app.state.telemetry.append_turn(cid, question, result.answer, max_messages=20)

        return {
            "type": "message",
            "text": result.answer,
            "sources": result.sources,
            "tools_used": result.tools_used,
            "conversation_id": cid,
        }

    return router
