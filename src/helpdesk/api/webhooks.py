"""Slack and Microsoft Teams webhook adapters for the helpdesk agent."""

from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel

from helpdesk.agent import HelpdeskAgent

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


def build_webhook_router(app: FastAPI) -> APIRouter:
    router = APIRouter(prefix="/webhooks", tags=["webhooks"])

    @router.post("/slack")
    async def slack_webhook(body: SlackWebhookPayload) -> dict[str, Any]:
        if body.type == "url_verification" and body.challenge is not None:
            return {"challenge": body.challenge}

        event = body.event or {}
        question = (body.text or str(event.get("text") or "")).strip()
        if not question:
            raise HTTPException(status_code=400, detail="Missing message text in Slack payload")

        channel = body.channel_id or str(event.get("channel") or "default")
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
    async def teams_webhook(body: TeamsWebhookPayload) -> dict[str, Any]:
        question = strip_teams_mentions(body.text)
        if not question:
            raise HTTPException(status_code=400, detail="Missing message text in Teams payload")

        conv_id = str((body.conversation or {}).get("id") or "default")
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
