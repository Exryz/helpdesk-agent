"""Request/LLM-call telemetry stored in SQLite: tokens, cost, latency, tools, errors.

Designed so it can later be exported to a time-series DB (InfluxDB) + Grafana.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from contextvars import ContextVar
from pathlib import Path
from typing import Any

_current_request: ContextVar[str | None] = ContextVar("current_request", default=None)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS requests (
    id TEXT PRIMARY KEY,
    ts REAL NOT NULL,
    conversation_id TEXT,
    question TEXT,
    latency_ms REAL,
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    cost_usd REAL DEFAULT 0,
    llm_calls INTEGER DEFAULT 0,
    tools_used TEXT DEFAULT '[]',
    sources TEXT DEFAULT '[]',
    error TEXT
);
CREATE TABLE IF NOT EXISTS llm_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT,
    ts REAL NOT NULL,
    model TEXT,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    cost_usd REAL,
    latency_ms REAL,
    error TEXT
);
CREATE INDEX IF NOT EXISTS idx_llm_calls_request ON llm_calls(request_id);
CREATE TABLE IF NOT EXISTS conversation_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    ts REAL NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_conv_messages_cid ON conversation_messages(conversation_id, id);
"""


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, round(pct / 100 * (len(ordered) - 1))))
    return ordered[idx]


class Telemetry:
    def __init__(self, path: Path | str = ":memory:"):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conn.executescript(_SCHEMA)

    # ---- request scope ------------------------------------------------------------------
    def start_request(self, question: str, conversation_id: str | None = None) -> str:
        rid = uuid.uuid4().hex[:12]
        with self._lock:
            self._conn.execute(
                "INSERT INTO requests (id, ts, conversation_id, question) VALUES (?, ?, ?, ?)",
                (rid, time.time(), conversation_id, question),
            )
            self._conn.commit()
        _current_request.set(rid)
        return rid

    def finish_request(
        self,
        request_id: str,
        latency_ms: float,
        tools_used: list[str],
        sources: list[str],
        error: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            agg = self._conn.execute(
                "SELECT COUNT(*) n, COALESCE(SUM(prompt_tokens),0) pt, "
                "COALESCE(SUM(completion_tokens),0) ct, COALESCE(SUM(cost_usd),0) cost "
                "FROM llm_calls WHERE request_id = ?",
                (request_id,),
            ).fetchone()
            self._conn.execute(
                "UPDATE requests SET latency_ms=?, prompt_tokens=?, completion_tokens=?, "
                "cost_usd=?, llm_calls=?, tools_used=?, sources=?, error=? WHERE id=?",
                (latency_ms, agg["pt"], agg["ct"], agg["cost"], agg["n"],
                 json.dumps(tools_used), json.dumps(sources), error, request_id),
            )
            self._conn.commit()
        _current_request.set(None)
        return {
            "request_id": request_id,
            "latency_ms": round(latency_ms, 1),
            "llm_calls": agg["n"],
            "prompt_tokens": agg["pt"],
            "completion_tokens": agg["ct"],
            "cost_usd": round(agg["cost"], 6),
        }

    def record_llm_call(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: float,
        latency_ms: float,
        error: str | None = None,
    ) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO llm_calls (request_id, ts, model, prompt_tokens, completion_tokens, "
                "cost_usd, latency_ms, error) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (_current_request.get(), time.time(), model, prompt_tokens, completion_tokens,
                 cost_usd, latency_ms, error),
            )
            self._conn.commit()

    # ---- reporting ----------------------------------------------------------------------
    def summary(self, since_ts: float | None = None) -> dict[str, Any]:
        where, params = ("WHERE latency_ms IS NOT NULL", [])
        if since_ts is not None:
            where += " AND ts >= ?"
            params.append(since_ts)
        with self._lock:
            rows = self._conn.execute(f"SELECT * FROM requests {where}", params).fetchall()
        latencies = [r["latency_ms"] for r in rows]
        tool_counts: dict[str, int] = {}
        for r in rows:
            for t in json.loads(r["tools_used"] or "[]"):
                tool_counts[t] = tool_counts.get(t, 0) + 1
        n = len(rows)
        total_cost = sum(r["cost_usd"] or 0 for r in rows)
        return {
            "requests": n,
            "errors": sum(1 for r in rows if r["error"]),
            "latency_ms": {
                "avg": round(sum(latencies) / n, 1) if n else 0.0,
                "p50": round(_percentile(latencies, 50), 1),
                "p95": round(_percentile(latencies, 95), 1),
            },
            "tokens": {
                "prompt": sum(r["prompt_tokens"] or 0 for r in rows),
                "completion": sum(r["completion_tokens"] or 0 for r in rows),
            },
            "cost_usd": {
                "total": round(total_cost, 6),
                "avg_per_request": round(total_cost / n, 6) if n else 0.0,
            },
            "tool_usage": dict(sorted(tool_counts.items(), key=lambda x: -x[1])),
        }

    def recent(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM requests WHERE latency_ms IS NOT NULL ORDER BY ts DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    # ---- persistent conversation history ------------------------------------------------
    def get_history(self, conversation_id: str, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT role, content FROM ("
                "  SELECT id, role, content FROM conversation_messages "
                "  WHERE conversation_id = ? ORDER BY id DESC LIMIT ?"
                ") ORDER BY id ASC",
                (conversation_id, limit),
            ).fetchall()
        return [{"role": str(r["role"]), "content": str(r["content"])} for r in rows]

    def append_turn(
        self,
        conversation_id: str,
        user_message: str,
        assistant_message: str,
        max_messages: int = 20,
    ) -> None:
        now = time.time()
        with self._lock:
            self._conn.executemany(
                "INSERT INTO conversation_messages (conversation_id, ts, role, content) "
                "VALUES (?, ?, ?, ?)",
                [
                    (conversation_id, now, "user", user_message),
                    (conversation_id, now, "assistant", assistant_message),
                ],
            )
            self._conn.execute(
                "DELETE FROM conversation_messages WHERE conversation_id = ? AND id NOT IN ("
                "  SELECT id FROM conversation_messages WHERE conversation_id = ? "
                "  ORDER BY id DESC LIMIT ?"
                ")",
                (conversation_id, conversation_id, max_messages),
            )
            self._conn.commit()

    def clear_history(self, conversation_id: str) -> int:
        with self._lock:
            cur = self._conn.execute(
                "DELETE FROM conversation_messages WHERE conversation_id = ?",
                (conversation_id,),
            )
            self._conn.commit()
            return int(cur.rowcount or 0)

