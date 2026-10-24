"""FastAPI application exposing /chat, /metrics, /health, and ticket management."""

from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Query
from pydantic import BaseModel

from helpdesk.agent import HelpdeskAgent, build_tool_backend
from helpdesk.config import Settings, get_settings
from helpdesk.llm import LiteLLMClient
from helpdesk.retrieval import build_retriever
from helpdesk.telemetry import Telemetry
from helpdesk.tickets.api import build_router
from helpdesk.tickets.portal import build_portal_router
from helpdesk.tickets.repository import TicketRepository


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

        yield

        # Shutdown cleanup
        backend_to_close = getattr(app.state, "tool_backend", None)
        if backend_to_close and hasattr(backend_to_close, "aclose"):
            await backend_to_close.aclose()

    app = FastAPI(title="Northwind Labs IT Helpdesk API", version="0.1.0", lifespan=lifespan)
    app.state.agent = agent
    app.state.telemetry = actual_telemetry
    app.state.repo = actual_repo
    app.state.conversations = conversations

    # Mount ticket management and HTML portal routers
    app.include_router(build_router(actual_repo))
    app.include_router(build_portal_router(actual_repo))

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest) -> ChatResponse:
        current_agent: HelpdeskAgent = app.state.agent
        cid = request.conversation_id or uuid.uuid4().hex[:12]

        history_to_use = list(request.history) if request.history is not None else list(conversations[cid])

        result = await current_agent.run(
            question=request.message,
            history=history_to_use,
            conversation_id=cid,
        )

        # Update in-memory history: cap at last 10 turns (20 messages)
        new_history = list(history_to_use)
        new_history.append({"role": "user", "content": request.message})
        new_history.append({"role": "assistant", "content": result.answer})
        if len(new_history) > 20:
            new_history = new_history[-20:]
        conversations[cid] = new_history

        return ChatResponse(
            answer=result.answer,
            sources=result.sources,
            tools_used=result.tools_used,
            tool_calls=result.tool_calls,
            conversation_id=cid,
            stats=result.stats,
        )

    @app.get("/metrics")
    def metrics(
        since_ts: float | None = Query(None, description="Filter requests since timestamp"),
    ) -> dict[str, Any]:
        return app.state.telemetry.summary(since_ts=since_ts)

    @app.get("/metrics/recent")
    def recent_metrics(limit: int = Query(20, ge=1, le=100)) -> list[dict[str, Any]]:
        return app.state.telemetry.recent(limit=limit)

    return app


def app_factory() -> FastAPI:
    """Factory function for uvicorn: uvicorn helpdesk.api.main:app_factory --factory."""
    return create_app()
