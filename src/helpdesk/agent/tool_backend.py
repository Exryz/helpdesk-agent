"""Pluggable tool backends: in-process (LocalToolBackend) or via MCP (McpToolBackend)."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from contextlib import AsyncExitStack
from typing import Any, Protocol

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from helpdesk.config import Settings, get_settings
from helpdesk.tickets.repository import TicketRepository
from helpdesk.tickets.tools import TICKET_TOOL_SCHEMAS, TicketTools


class ToolBackend(Protocol):
    async def schemas(self) -> list[dict[str, Any]]: ...

    async def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]: ...

    async def aclose(self) -> None: ...


class LocalToolBackend:
    """Runs ticket tools in-process against a TicketTools instance."""

    def __init__(self, tools: TicketTools):
        self.tools = tools

    async def schemas(self) -> list[dict[str, Any]]:
        return list(TICKET_TOOL_SCHEMAS)

    async def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.tools.call(name, arguments)

    async def aclose(self) -> None:
        pass


class McpToolBackend:
    """Spawns an out-of-process MCP server over stdio and communicates via MCP protocol."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path
        self._runner: asyncio.Task[None] | None = None
        self._stop: asyncio.Event | None = None
        self._session: ClientSession | None = None
        self._lock = asyncio.Lock()

    async def _ensure_session(self) -> ClientSession:
        if self._session is not None:
            return self._session

        async with self._lock:
            if self._session is not None:
                return self._session

            env = dict(os.environ)
            if self.db_path:
                env["HELPDESK_TICKETS_DB"] = str(self.db_path)

            # Ensure subprocess can find helpdesk package
            src_dir = str(get_settings().kb_dir.parents[1] / "src")
            current_py_path = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = (
                f"{src_dir}{os.pathsep}{current_py_path}" if current_py_path else src_dir
            )

            params = StdioServerParameters(
                command=sys.executable,
                args=["-m", "helpdesk.mcp_server.server"],
                env=env,
            )

            # anyio cancel scopes must be exited by the task that entered them, so the whole
            # session lifetime is owned by one dedicated task (see _run).
            ready: asyncio.Future[ClientSession] = asyncio.get_running_loop().create_future()
            self._stop = asyncio.Event()
            self._runner = asyncio.create_task(self._run(params, ready, self._stop))
            return await ready

    async def _run(
        self,
        params: StdioServerParameters,
        ready: asyncio.Future[ClientSession],
        stop: asyncio.Event,
    ) -> None:
        try:
            async with AsyncExitStack() as stack:
                read, write = await stack.enter_async_context(stdio_client(params))
                session = await stack.enter_async_context(ClientSession(read, write))
                await session.initialize()
                self._session = session
                ready.set_result(session)
                await stop.wait()
        except Exception as e:
            if not ready.done():
                ready.set_exception(e)
        finally:
            self._session = None

    async def schemas(self) -> list[dict[str, Any]]:
        session = await self._ensure_session()
        tools_result = await session.list_tools()
        schemas_list: list[dict[str, Any]] = []
        for t in tools_result.tools:
            schemas_list.append(
                {
                    "name": t.name,
                    "description": t.description or "",
                    "parameters": t.inputSchema if isinstance(t.inputSchema, dict) else {},
                }
            )
        return schemas_list

    async def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        session = await self._ensure_session()
        try:
            res = await session.call_tool(name, arguments)
        except Exception as e:
            return {"error": str(e)}

        if getattr(res, "isError", False):
            err_text = ""
            if getattr(res, "content", None):
                for item in res.content:
                    text_val = getattr(item, "text", None)
                    if text_val:
                        err_text += str(text_val)
            return {"error": err_text or "Tool call reported error"}

        # Prefer structured content if available
        structured = getattr(res, "structuredContent", None)
        if isinstance(structured, dict):
            return structured

        # Otherwise parse JSON text from content
        if getattr(res, "content", None):
            for item in res.content:
                text = getattr(item, "text", None)
                if text:
                    try:
                        parsed = json.loads(text)
                        if isinstance(parsed, dict):
                            return parsed
                    except json.JSONDecodeError:
                        return {"text": text}

        return {}

    async def aclose(self) -> None:
        async with self._lock:
            if self._runner is not None:
                if self._stop is not None:
                    self._stop.set()
                await self._runner
                self._runner = None
                self._stop = None
                self._session = None


def build_tool_backend(settings: Settings | None = None) -> ToolBackend:
    s = settings or get_settings()
    if s.tool_backend == "local":
        repo = TicketRepository.from_path(s.tickets_db)
        return LocalToolBackend(TicketTools(repo))
    return McpToolBackend(db_path=str(s.tickets_db))
