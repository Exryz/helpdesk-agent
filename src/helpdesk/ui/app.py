"""Chainlit chat interface for Helpdesk Agent."""

from __future__ import annotations

import json
from typing import Any

import chainlit as cl

from helpdesk.agent import HelpdeskAgent, build_tool_backend
from helpdesk.browser import extract_screenshot_paths
from helpdesk.config import get_settings
from helpdesk.llm import LiteLLMClient
from helpdesk.retrieval import build_retriever
from helpdesk.telemetry import Telemetry


def _init_agent() -> HelpdeskAgent:
    settings = get_settings()
    telemetry = Telemetry(settings.telemetry_db)
    retriever = build_retriever(settings)
    backend = build_tool_backend(settings)
    llm = LiteLLMClient(
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        timeout_s=settings.llm_timeout_s,
        telemetry=telemetry,
    )
    return HelpdeskAgent(llm, retriever, backend, settings=settings, telemetry=telemetry)


@cl.on_chat_start
async def on_chat_start() -> None:
    agent = _init_agent()
    cl.user_session.set("agent", agent)
    cl.user_session.set("history", [])
    await cl.Message(
        content="Hello! I am Northwind Labs IT Helpdesk Assistant. How can I help you today?"
    ).send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    agent: HelpdeskAgent = cl.user_session.get("agent")
    history: list[dict[str, Any]] = cl.user_session.get("history") or []

    result = await agent.run(message.content, history=history)

    # Display tool calls as steps
    for tc in result.tool_calls:
        async with cl.Step(name=f"Tool: {tc['name']}", type="tool") as step:
            step.input = json.dumps(tc.get("arguments", {}), indent=2)
            step.output = json.dumps(tc.get("result", {}), indent=2)

    # Display consulted knowledge base sources
    if result.sources:
        async with cl.Step(name="Sources Consulted", type="tool") as step:
            sources_md = "\n".join(
                f"- **[{s['doc_id']}]** {s['title']} ({s['section']})" for s in result.sources
            )
            step.output = sources_md

    # Format latency and cost footer
    stats = result.stats or {}
    cost = stats.get("cost_usd", 0.0)
    latency = stats.get("latency_ms", 0.0)
    footer = f"\n\n---\n*Cost: ${cost:.5f} | Latency: {latency:.0f}ms*"

    # Attach any ticket form preview screenshots captured by Playwright
    elements = [
        cl.Image(name=f"ticket_form_preview_{i + 1}", path=path, display="inline")
        for i, path in enumerate(extract_screenshot_paths(result.tool_calls))
    ]

    # Update in-memory session history (keep last 10 turns = 20 messages)
    history.append({"role": "user", "content": message.content})
    history.append({"role": "assistant", "content": result.answer})
    if len(history) > 20:
        history = history[-20:]
    cl.user_session.set("history", history)

    await cl.Message(content=result.answer + footer, elements=elements).send()
