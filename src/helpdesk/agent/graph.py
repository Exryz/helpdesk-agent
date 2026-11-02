"""LangGraph agent coordinating hybrid retrieval, LiteLLM, and ticket tools."""

from __future__ import annotations

import asyncio
import contextvars
import json
import re
import time
from collections.abc import AsyncIterator
from typing import Any

from langgraph.graph import END, START, StateGraph

from helpdesk.agent.prompts import SYSTEM_PROMPT
from helpdesk.agent.state import AgentResult, AgentState
from helpdesk.agent.tool_backend import ToolBackend
from helpdesk.config import Settings, get_settings
from helpdesk.llm import LLMClient, LLMResponse
from helpdesk.retrieval.hybrid import HybridRetriever, RetrievedChunk
from helpdesk.telemetry import Telemetry

SEARCH_KB_SCHEMA: dict[str, Any] = {
    "name": "search_kb",
    "description": (
        "Search the IT knowledge base for documentation, guides, troubleshooting steps, "
        "and company IT policies."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Keywords or search phrase to look up in the knowledge base.",
            }
        },
        "required": ["query"],
    },
}

_stream_queue_var: contextvars.ContextVar[asyncio.Queue[dict[str, Any]] | None] = contextvars.ContextVar(
    "_stream_queue_var", default=None
)


class HelpdeskAgent:
    def __init__(
        self,
        llm: LLMClient,
        retriever: HybridRetriever,
        tools: ToolBackend,
        settings: Settings | None = None,
        telemetry: Telemetry | None = None,
    ):
        self.llm = llm
        self.retriever = retriever
        self.tools = tools
        self.settings = settings or get_settings()
        self.telemetry = telemetry
        self._graph = self._build_graph()

    def _format_chunks(self, chunks: list[RetrievedChunk]) -> str:
        if not chunks:
            return "No relevant knowledge base articles found."
        entries: list[str] = []
        for c in chunks:
            entries.append(
                f"[{c.chunk.doc_id}] {c.chunk.title} - Section: {c.chunk.section}\n{c.chunk.text}"
            )
        return "\n\n---\n\n".join(entries)

    def _build_graph(self) -> Any:
        workflow = StateGraph(AgentState)

        async def retrieve_node(state: AgentState) -> dict[str, Any]:
            q = state["question"]
            chunks = await asyncio.to_thread(self.retriever.search, q, k=self.settings.top_k)
            context_str = self._format_chunks(chunks)

            seen_ids: set[str] = set()
            doc_ids: list[str] = []
            for c in chunks:
                if c.chunk.doc_id not in seen_ids:
                    seen_ids.add(c.chunk.doc_id)
                    doc_ids.append(c.chunk.doc_id)

            queue = _stream_queue_var.get()
            if queue is not None:
                await queue.put({"type": "retrieval", "doc_ids": doc_ids})

            sys_content = f"{SYSTEM_PROMPT}\n\nKnowledge Base Context:\n{context_str}"
            messages: list[dict[str, Any]] = [{"role": "system", "content": sys_content}]
            if state.get("history"):
                messages.extend(state["history"])
            messages.append({"role": "user", "content": q})

            return {
                "messages": messages,
                "retrieved_chunks": list(chunks),
                "tools_used": [],
                "tool_calls": [],
                "steps": 0,
            }

        async def agent_node(state: AgentState) -> dict[str, Any]:
            steps = state.get("steps", 0) + 1
            messages = list(state.get("messages", []))
            queue = _stream_queue_var.get()

            if steps >= self.settings.max_agent_steps:
                # Capped at max steps: force a final answer without tools
                resp: LLMResponse | None = None
                if queue is not None and hasattr(self.llm, "chat_stream"):
                    async for ev in self.llm.chat_stream(messages, tools=None):
                        if ev.kind == "delta" and ev.text:
                            await queue.put({"type": "token", "text": ev.text})
                        elif ev.kind == "response":
                            resp = ev.response
                    if resp is None:
                        raise RuntimeError("LLM stream ended without response")
                else:
                    resp = await self.llm.chat(messages, tools=None)
                    if queue is not None and resp.content:
                        await queue.put({"type": "token", "text": resp.content})

                ans = resp.content or ""
                return {
                    "messages": messages + [resp.as_message()],
                    "steps": steps,
                    "final_answer": ans,
                    "last_response": resp,
                }

            backend_schemas = await self.tools.schemas()
            all_tools = [SEARCH_KB_SCHEMA] + backend_schemas

            resp = None
            if queue is not None and hasattr(self.llm, "chat_stream"):
                async for ev in self.llm.chat_stream(messages, tools=all_tools):
                    if ev.kind == "delta" and ev.text:
                        await queue.put({"type": "token", "text": ev.text})
                    elif ev.kind == "response":
                        resp = ev.response
                if resp is None:
                    raise RuntimeError("LLM stream ended without response")
            else:
                resp = await self.llm.chat(messages, tools=all_tools)
                if queue is not None and resp.content and not resp.tool_calls:
                    await queue.put({"type": "token", "text": resp.content})

            if not resp.tool_calls:
                return {
                    "messages": messages + [resp.as_message()],
                    "steps": steps,
                    "final_answer": resp.content or "",
                    "last_response": resp,
                }

            return {
                "messages": messages + [resp.as_message()],
                "steps": steps,
                "last_response": resp,
            }

        def should_continue(state: AgentState) -> str:
            if state.get("final_answer") is not None:
                return END
            if state.get("steps", 0) >= self.settings.max_agent_steps:
                return END
            last_resp = state.get("last_response")
            if not last_resp or not last_resp.tool_calls:
                return END
            return "tools"

        async def tools_node(state: AgentState) -> dict[str, Any]:
            last_resp = state.get("last_response")
            if not last_resp or not last_resp.tool_calls:
                return {}

            messages = list(state.get("messages", []))
            retrieved = list(state.get("retrieved_chunks", []))
            tools_used = list(state.get("tools_used", []))
            tool_calls = list(state.get("tool_calls", []))
            queue = _stream_queue_var.get()

            for tc in last_resp.tool_calls:
                if queue is not None:
                    await queue.put(
                        {
                            "type": "tool_call",
                            "name": tc.name,
                            "arguments": tc.arguments,
                        }
                    )

                if tc.name == "search_kb":
                    query = tc.arguments.get("query", "")
                    kb_hits = await asyncio.to_thread(
                        self.retriever.search, query, k=self.settings.top_k
                    )
                    retrieved.extend(kb_hits)
                    res: dict[str, Any] = {"results": [c.to_dict() for c in kb_hits]}
                else:
                    res = await self.tools.call(tc.name, tc.arguments)
                    if tc.name not in tools_used:
                        tools_used.append(tc.name)

                if queue is not None:
                    await queue.put(
                        {
                            "type": "tool_result",
                            "name": tc.name,
                            "result": res,
                        }
                    )

                tool_calls.append({"name": tc.name, "arguments": tc.arguments, "result": res})
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": tc.name,
                        "content": json.dumps(res),
                    }
                )

            return {
                "messages": messages,
                "retrieved_chunks": retrieved,
                "tools_used": tools_used,
                "tool_calls": tool_calls,
            }

        workflow.add_node("retrieve", retrieve_node)
        workflow.add_node("agent", agent_node)
        workflow.add_node("tools", tools_node)

        workflow.add_edge(START, "retrieve")
        workflow.add_edge("retrieve", "agent")
        workflow.add_conditional_edges("agent", should_continue, ["tools", END])
        workflow.add_edge("tools", "agent")

        return workflow.compile()

    def _build_result(
        self,
        final_state: dict[str, Any],
        start_time: float,
        req_id: str | None,
    ) -> AgentResult:
        answer = final_state.get("final_answer")
        if not answer:
            for msg in reversed(final_state.get("messages", [])):
                if msg.get("role") == "assistant" and msg.get("content"):
                    answer = msg["content"]
                    break
        if not answer:
            answer = "I could not generate an answer with the available information."

        retrieved_chunks = final_state.get("retrieved_chunks", [])
        # Sources = retrieved articles the answer actually cites, one entry per article.
        cited = set(re.findall(r"KB-\d+", answer))
        seen_sources: set[str] = set()
        sources: list[dict[str, Any]] = []
        for rc in retrieved_chunks:
            key = rc.chunk.doc_id
            if key not in seen_sources and key in cited:
                seen_sources.add(key)
                sources.append(
                    {
                        "doc_id": rc.chunk.doc_id,
                        "title": rc.chunk.title,
                        "section": rc.chunk.section,
                    }
                )

        seen_ids: set[str] = set()
        retrieved_doc_ids: list[str] = []
        for rc in retrieved_chunks:
            if rc.chunk.doc_id not in seen_ids:
                seen_ids.add(rc.chunk.doc_id)
                retrieved_doc_ids.append(rc.chunk.doc_id)

        tools_used = final_state.get("tools_used", [])
        tool_calls = final_state.get("tool_calls", [])
        steps = final_state.get("steps", 0)

        latency_ms = (time.perf_counter() - start_time) * 1000
        stats: dict[str, Any] = {}
        if self.telemetry and req_id:
            stats = self.telemetry.finish_request(
                request_id=req_id,
                latency_ms=latency_ms,
                tools_used=tools_used,
                sources=retrieved_doc_ids,
                error=None,
            )

        return AgentResult(
            answer=answer,
            sources=sources,
            tools_used=tools_used,
            tool_calls=tool_calls,
            retrieved_doc_ids=retrieved_doc_ids,
            stats=stats,
            steps=steps,
        )

    def _record_error(self, req_id: str | None, start_time: float, exc: Exception) -> None:
        latency_ms = (time.perf_counter() - start_time) * 1000
        if self.telemetry and req_id:
            self.telemetry.finish_request(
                request_id=req_id,
                latency_ms=latency_ms,
                tools_used=[],
                sources=[],
                error=repr(exc),
            )

    async def run(
        self,
        question: str,
        history: list[dict[str, Any]] | None = None,
        conversation_id: str | None = None,
    ) -> AgentResult:
        start_time = time.perf_counter()
        req_id: str | None = None
        if self.telemetry:
            req_id = self.telemetry.start_request(question, conversation_id=conversation_id)

        initial_state: AgentState = {
            "question": question,
            "history": list(history) if history else [],
        }

        try:
            final_state = await self._graph.ainvoke(initial_state)
            return self._build_result(final_state, start_time, req_id)
        except Exception as exc:
            self._record_error(req_id, start_time, exc)
            raise

    async def astream(
        self,
        question: str,
        history: list[dict[str, Any]] | None = None,
        conversation_id: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        start_time = time.perf_counter()
        req_id: str | None = None
        if self.telemetry:
            req_id = self.telemetry.start_request(question, conversation_id=conversation_id)

        initial_state: AgentState = {
            "question": question,
            "history": list(history) if history else [],
        }

        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        token = _stream_queue_var.set(queue)

        graph_task = asyncio.create_task(self._graph.ainvoke(initial_state))

        try:
            while True:
                get_task = asyncio.create_task(queue.get())
                done, _ = await asyncio.wait(
                    [graph_task, get_task],
                    return_when=asyncio.FIRST_COMPLETED,
                )
                if get_task in done:
                    yield get_task.result()
                else:
                    get_task.cancel()
                    break

            while not queue.empty():
                yield queue.get_nowait()

            final_state = await graph_task
            result = self._build_result(final_state, start_time, req_id)
            yield {"type": "done", "result": result.to_dict()}
        except Exception as exc:
            self._record_error(req_id, start_time, exc)
            if not graph_task.done():
                graph_task.cancel()
            raise
        finally:
            _stream_queue_var.reset(token)
