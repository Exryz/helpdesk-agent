"""FastAPI application exposing /chat, /kb, /sla, /metrics, /health, and ticket management."""

from __future__ import annotations

import asyncio
import json
import uuid
from collections import defaultdict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from typing import Any

from fastapi import FastAPI, Query
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel

from helpdesk.agent import HelpdeskAgent, build_tool_backend
from helpdesk.api.kb import build_kb_router
from helpdesk.api.webhooks import build_webhook_router
from helpdesk.config import Settings, get_settings
from helpdesk.llm import LiteLLMClient
from helpdesk.retrieval import build_retriever
from helpdesk.retrieval.watcher import watch_kb
from helpdesk.telemetry import Telemetry
from helpdesk.tickets.api import build_router
from helpdesk.tickets.portal import build_portal_router
from helpdesk.tickets.repository import TicketRepository
from helpdesk.tickets.sla import build_sla_router


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    history: list[dict[str, Any]] | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[dict[str, Any]]
    tools_used: list[str]
    tool_calls: list[dict[str, Any]]
    conversation_id: str
    stats: dict[str, Any]


def create_app(
    agent: HelpdeskAgent | None = None,
    telemetry: Telemetry | None = None,
    repo: TicketRepository | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    s = settings or get_settings()
    actual_telemetry = telemetry or Telemetry(s.telemetry_db)
    actual_repo = repo or TicketRepository.from_path(s.tickets_db)

    # In-memory conversation store: conversation_id -> list of turn messages (max 20 msgs)
    conversations: dict[str, list[dict[str, Any]]] = defaultdict(list)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        nonlocal agent
        if agent is None:
            retriever = build_retriever(s)
            backend = build_tool_backend(s)
            llm = LiteLLMClient(
                model=s.llm_model,
                temperature=s.llm_temperature,
                timeout_s=s.llm_timeout_s,
                telemetry=actual_telemetry,
            )
            agent = HelpdeskAgent(llm, retriever, backend, settings=s, telemetry=actual_telemetry)
            app.state.agent = agent
            app.state.tool_backend = backend
        else:
            app.state.agent = agent
            app.state.tool_backend = getattr(agent, "tools", None)

        watcher_stop = asyncio.Event()
        watcher_task: asyncio.Task[None] | None = None
        if s.kb_watch_interval_s > 0:
            watcher_task = asyncio.create_task(
                watch_kb(app.state.agent, s, s.kb_watch_interval_s, watcher_stop)
            )

        yield

        # Shutdown cleanup
        if watcher_task is not None:
            watcher_stop.set()
            watcher_task.cancel()
            with suppress(asyncio.CancelledError):
                await watcher_task
        backend_to_close = getattr(app.state, "tool_backend", None)
        if backend_to_close and hasattr(backend_to_close, "aclose"):
            await backend_to_close.aclose()

    app = FastAPI(title="Northwind Labs IT Helpdesk API", version="0.1.0", lifespan=lifespan)
    app.state.settings = s
    app.state.agent = agent
    app.state.telemetry = actual_telemetry
    app.state.repo = actual_repo
    app.state.conversations = conversations

    # Mount ticket management, SLA, KB, HTML portal, and Slack/Teams webhook routers
    app.include_router(build_router(actual_repo))
    app.include_router(build_sla_router(actual_repo, s))
    app.include_router(build_kb_router(app))
    app.include_router(build_portal_router(actual_repo))
    app.include_router(build_webhook_router(app))

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest) -> ChatResponse:
        current_agent: HelpdeskAgent = app.state.agent
        cid = request.conversation_id or uuid.uuid4().hex[:12]

        history_to_use = (
            list(request.history)
            if request.history is not None
            else app.state.telemetry.get_history(cid, limit=20)
        )

        result = await current_agent.run(
            question=request.message,
            history=history_to_use,
            conversation_id=cid,
        )

        # Persist conversation turn in SQLite (capped at last 10 turns = 20 messages)
        app.state.telemetry.append_turn(
            conversation_id=cid,
            user_message=request.message,
            assistant_message=result.answer,
            max_messages=20,
        )
        conversations[cid] = app.state.telemetry.get_history(cid, limit=20)

        return ChatResponse(
            answer=result.answer,
            sources=result.sources,
            tools_used=result.tools_used,
            tool_calls=result.tool_calls,
            conversation_id=cid,
            stats=result.stats,
        )

    @app.post("/chat/stream")
    async def chat_stream(request: ChatRequest) -> StreamingResponse:
        current_agent: HelpdeskAgent = app.state.agent
        cid = request.conversation_id or uuid.uuid4().hex[:12]
        history_to_use = (
            list(request.history)
            if request.history is not None
            else app.state.telemetry.get_history(cid, limit=20)
        )

        async def event_generator() -> AsyncIterator[str]:
            final_answer = ""
            async for ev in current_agent.astream(
                question=request.message,
                history=history_to_use,
                conversation_id=cid,
            ):
                ev_type = ev.get("type")
                if ev_type == "retrieval":
                    yield f"event: retrieval\ndata: {json.dumps({'doc_ids': ev.get('doc_ids', [])})}\n\n"
                elif ev_type == "tool_call":
                    payload = {"name": ev.get("name"), "arguments": ev.get("arguments", {})}
                    yield f"event: tool_call\ndata: {json.dumps(payload)}\n\n"
                elif ev_type == "tool_result":
                    payload = {"name": ev.get("name"), "result": ev.get("result", {})}
                    yield f"event: tool_result\ndata: {json.dumps(payload)}\n\n"
                elif ev_type == "token":
                    piece = ev.get("text", "")
                    yield f"event: token\ndata: {json.dumps({'token': piece, 'text': piece})}\n\n"
                elif ev_type == "done":
                    result_dict = ev.get("result", {})
                    final_answer = result_dict.get("answer", "")
                    done_payload = dict(result_dict)
                    done_payload["conversation_id"] = cid
                    yield f"event: done\ndata: {json.dumps(done_payload)}\n\n"

            app.state.telemetry.append_turn(
                conversation_id=cid,
                user_message=request.message,
                assistant_message=final_answer,
                max_messages=20,
            )
            conversations[cid] = app.state.telemetry.get_history(cid, limit=20)

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    @app.get("/metrics")
    def metrics(
        since_ts: float | None = Query(None, description="Filter requests since timestamp"),
    ) -> dict[str, Any]:
        return app.state.telemetry.summary(since_ts=since_ts)

    @app.get("/metrics/recent")
    def recent_metrics(limit: int = Query(20, ge=1, le=100)) -> list[dict[str, Any]]:
        return app.state.telemetry.recent(limit=limit)

    @app.get("/metrics/influx", response_class=PlainTextResponse)
    def influx_metrics(limit: int = Query(100, ge=1, le=1000)) -> PlainTextResponse:
        return PlainTextResponse(content=app.state.telemetry.to_influx_lines(limit=limit))

    @app.get("/conversations/{conversation_id}")
    def get_conversation(conversation_id: str) -> dict[str, Any]:
        messages = app.state.telemetry.get_history(conversation_id, limit=20)
        return {"conversation_id": conversation_id, "messages": messages}

    @app.delete("/conversations/{conversation_id}")
    def delete_conversation(conversation_id: str) -> dict[str, Any]:
        deleted = app.state.telemetry.clear_history(conversation_id)
        conversations.pop(conversation_id, None)
        return {"conversation_id": conversation_id, "deleted_messages": deleted}

    return app


def app_factory() -> FastAPI:
    """Factory function for uvicorn: uvicorn helpdesk.api.main:app_factory --factory."""
    return create_app()
