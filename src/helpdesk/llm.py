"""Provider-agnostic LLM client (LiteLLM) plus a scripted fake for tests."""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator, Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from helpdesk.config import get_settings
from helpdesk.telemetry import Telemetry

Message = dict[str, Any]


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]

    def to_openai(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": "function",
            "function": {"name": self.name, "arguments": json.dumps(self.arguments)},
        }


@dataclass
class LLMResponse:
    content: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0

    def as_message(self) -> Message:
        msg: Message = {"role": "assistant", "content": self.content or ""}
        if self.tool_calls:
            msg["tool_calls"] = [tc.to_openai() for tc in self.tool_calls]
        return msg


@dataclass
class StreamEvent:
    kind: Literal["delta", "response"]
    text: str = ""
    response: LLMResponse | None = None


class LLMClient(Protocol):
    async def chat(
        self,
        messages: Sequence[Message],
        tools: Sequence[dict[str, Any]] | None = None,
        temperature: float | None = None,
        json_mode: bool = False,
    ) -> LLMResponse: ...

    def chat_stream(
        self,
        messages: Sequence[Message],
        tools: Sequence[dict[str, Any]] | None = None,
        temperature: float | None = None,
    ) -> AsyncIterator[StreamEvent]: ...


def _parse_args(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(raw or "{}")
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


_throttle_lock = asyncio.Lock()
_last_call_at: dict[str, float] = {}


async def _throttle(model: str, min_interval_s: float) -> None:
    """Space out calls to one model so free-tier rate limits (such as 5 req/min) are respected."""
    if min_interval_s <= 0:
        return
    async with _throttle_lock:
        wait = _last_call_at.get(model, 0.0) + min_interval_s - time.monotonic()
        if wait > 0:
            await asyncio.sleep(wait)
        _last_call_at[model] = time.monotonic()


class LiteLLMClient:
    """Any LiteLLM-supported model: 'gemini/...', 'azure/...', 'openai/...', 'ollama/...'."""

    def __init__(
        self,
        model: str,
        temperature: float = 0.1,
        timeout_s: float = 60.0,
        telemetry: Telemetry | None = None,
    ):
        self.model = model
        self.temperature = temperature
        self.timeout_s = timeout_s
        self.telemetry = telemetry

    async def chat(
        self,
        messages: Sequence[Message],
        tools: Sequence[dict[str, Any]] | None = None,
        temperature: float | None = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        import litellm

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": list(messages),
            "temperature": self.temperature if temperature is None else temperature,
            "timeout": self.timeout_s,
            "num_retries": 2,
        }
        if tools:
            kwargs["tools"] = [{"type": "function", "function": t} for t in tools]
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        await _throttle(self.model, get_settings().llm_min_interval_s)
        start = time.perf_counter()
        try:
            resp = await litellm.acompletion(**kwargs)
        except Exception as e:
            if self.telemetry:
                latency = (time.perf_counter() - start) * 1000
                self.telemetry.record_llm_call(self.model, 0, 0, 0.0, latency, error=repr(e))
            raise
        latency_ms = (time.perf_counter() - start) * 1000

        choice = resp.choices[0].message
        tool_calls = [
            ToolCall(
                id=tc.id or f"call_{i}",
                name=tc.function.name,
                arguments=_parse_args(tc.function.arguments),
            )
            for i, tc in enumerate(getattr(choice, "tool_calls", None) or [])
        ]
        usage = getattr(resp, "usage", None)
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        try:
            cost = float(litellm.completion_cost(completion_response=resp) or 0.0)
        except Exception:
            cost = 0.0  # unknown pricing for this model

        if self.telemetry:
            self.telemetry.record_llm_call(
                self.model, prompt_tokens, completion_tokens, cost, latency_ms
            )
        return LLMResponse(
            content=choice.content,
            tool_calls=tool_calls,
            model=self.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost,
            latency_ms=latency_ms,
        )

    async def chat_stream(
        self,
        messages: Sequence[Message],
        tools: Sequence[dict[str, Any]] | None = None,
        temperature: float | None = None,
    ) -> AsyncIterator[StreamEvent]:
        import litellm

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": list(messages),
            "temperature": self.temperature if temperature is None else temperature,
            "timeout": self.timeout_s,
            "num_retries": 2,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if tools:
            kwargs["tools"] = [{"type": "function", "function": t} for t in tools]

        await _throttle(self.model, get_settings().llm_min_interval_s)
        start = time.perf_counter()
        chunks: list[Any] = []
        try:
            response_stream = await litellm.acompletion(**kwargs)
            async for chunk in response_stream:
                chunks.append(chunk)
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    content = getattr(delta, "content", None)
                    if content:
                        yield StreamEvent(kind="delta", text=content)
        except Exception as e:
            if self.telemetry:
                latency = (time.perf_counter() - start) * 1000
                self.telemetry.record_llm_call(self.model, 0, 0, 0.0, latency, error=repr(e))
            raise
        latency_ms = (time.perf_counter() - start) * 1000

        rebuilt: Any = litellm.stream_chunk_builder(chunks, messages=list(messages))
        choices = getattr(rebuilt, "choices", None) or []
        first_choice = choices[0] if choices else None
        choice_msg = getattr(first_choice, "message", None)
        content = getattr(choice_msg, "content", None)
        tool_calls = [
            ToolCall(
                id=tc.id or f"call_{i}",
                name=tc.function.name,
                arguments=_parse_args(tc.function.arguments),
            )
            for i, tc in enumerate(getattr(choice_msg, "tool_calls", None) or [])
        ]
        usage = getattr(rebuilt, "usage", None)
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        try:
            cost = float(litellm.completion_cost(completion_response=rebuilt) or 0.0)
        except Exception:
            cost = 0.0

        if self.telemetry:
            self.telemetry.record_llm_call(
                self.model, prompt_tokens, completion_tokens, cost, latency_ms
            )

        resp = LLMResponse(
            content=content,
            tool_calls=tool_calls,
            model=self.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost,
            latency_ms=latency_ms,
        )
        yield StreamEvent(kind="response", response=resp)


Responder = Callable[[Sequence[Message], Sequence[dict[str, Any]] | None], LLMResponse]


class ScriptedLLM:
    """Deterministic fake LLM for tests: replays a list of responses or calls a function."""

    def __init__(
        self,
        script: Sequence[LLMResponse] | Responder,
        telemetry: Telemetry | None = None,
    ):
        self._script = script
        self._i = 0
        self.calls: list[list[Message]] = []
        self.telemetry = telemetry

    async def chat(
        self,
        messages: Sequence[Message],
        tools: Sequence[dict[str, Any]] | None = None,
        temperature: float | None = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        self.calls.append([dict(m) for m in messages])
        if callable(self._script):
            resp = self._script(messages, tools)
        else:
            if self._i >= len(self._script):
                raise RuntimeError("ScriptedLLM ran out of responses")
            resp = self._script[self._i]
            self._i += 1
        if self.telemetry:
            self.telemetry.record_llm_call(
                "scripted", resp.prompt_tokens, resp.completion_tokens, resp.cost_usd, 1.0
            )
        return resp

    async def chat_stream(
        self,
        messages: Sequence[Message],
        tools: Sequence[dict[str, Any]] | None = None,
        temperature: float | None = None,
    ) -> AsyncIterator[StreamEvent]:
        resp = await self.chat(messages, tools=tools, temperature=temperature)
        if resp.content:
            words = resp.content.split(" ")
            for i, word in enumerate(words):
                piece = word if i == 0 else f" {word}"
                yield StreamEvent(kind="delta", text=piece)
        yield StreamEvent(kind="response", response=resp)
