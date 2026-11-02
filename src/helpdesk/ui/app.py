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

    out_msg = cl.Message(content="")
    active_steps: dict[str, cl.Step] = {}
    result_dict: dict[str, Any] = {}

    async for ev in agent.astream(message.content, history=history):
        ev_type = ev.get("type")
        if ev_type == "tool_call":
            name = str(ev.get("name") or "")
            step = cl.Step(name=f"Tool: {name}", type="tool")
            step.input = json.dumps(ev.get("arguments", {}), indent=2)
            await step.send()
            active_steps[name] = step
        elif ev_type == "tool_result":
            name = str(ev.get("name") or "")
            existing_step = active_steps.get(name)
            if existing_step is not None:
                del active_steps[name]
                existing_step.output = json.dumps(ev.get("result", {}), indent=2)
                await existing_step.update()
        elif ev_type == "token":
            await out_msg.stream_token(ev.get("text", ""))
        elif ev_type == "done":
            result_dict = ev.get("result", {})

    # Display consulted knowledge base sources
    sources = result_dict.get("sources", [])
    if sources:
        async with cl.Step(name="Sources Consulted", type="tool") as step:
            sources_md = "\n".join(
                f"- **[{s['doc_id']}]** {s['title']} ({s['section']})" for s in sources
            )
            step.output = sources_md

    # Format latency and cost footer
    stats = result_dict.get("stats") or {}
    cost = stats.get("cost_usd", 0.0)
    latency = stats.get("latency_ms", 0.0)
    footer = f"\n\n---\n*Cost: ${cost:.5f} | Latency: {latency:.0f}ms*"
    await out_msg.stream_token(footer)

    # Attach any ticket form preview screenshots captured by Playwright
    elements: list[Any] = [
        cl.Image(name=f"ticket_form_preview_{i + 1}", path=path, display="inline")
        for i, path in enumerate(extract_screenshot_paths(result_dict.get("tool_calls", [])))
    ]
    if elements:
        out_msg.elements = elements

    await out_msg.send()

    # Update in-memory session history (keep last 10 turns = 20 messages)
    answer = result_dict.get("answer", "")
    history.append({"role": "user", "content": message.content})
    history.append({"role": "assistant", "content": answer})
    if len(history) > 20:
        history = history[-20:]
    cl.user_session.set("history", history)
