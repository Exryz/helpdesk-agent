"""Agent state definitions and result dataclass."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TypedDict

from helpdesk.llm import LLMResponse
from helpdesk.retrieval.hybrid import RetrievedChunk


@dataclass
class AgentResult:
    answer: str
    sources: list[dict[str, Any]]  # each {"doc_id", "title", "section"}, deduped
    tools_used: list[str]  # names of non-search_kb ticket tools executed
    tool_calls: list[dict[str, Any]]  # {"name", "arguments", "result"}
    retrieved_doc_ids: list[str]
    stats: dict[str, Any] = field(default_factory=dict)
    steps: int = 0


class AgentState(TypedDict, total=False):
    question: str
    history: list[dict[str, Any]]
    messages: list[dict[str, Any]]
    retrieved_chunks: list[RetrievedChunk]
    tools_used: list[str]
    tool_calls: list[dict[str, Any]]
    steps: int
    final_answer: str | None
    last_response: LLMResponse | None
