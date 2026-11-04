"""Knowledge base watcher and dynamic retriever reload."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from helpdesk.config import Settings, get_settings
from helpdesk.retrieval import build_retriever

logger = logging.getLogger("helpdesk.retrieval.watcher")


def kb_snapshot(kb_dir: Path | str) -> dict[str, float]:
    """Capture mtime snapshot of all Markdown articles in kb_dir."""
    p = Path(kb_dir)
    if not p.is_dir():
        return {}
    return {str(f.resolve()): f.stat().st_mtime for f in sorted(p.glob("*.md")) if f.is_file()}


def reload_retriever(agent: Any, settings: Settings | None = None) -> dict[str, Any]:
    """Rebuild retriever and swap agent.retriever.

    Reuses existing embedder and reranker instances (e.g. HashingEmbedder in tests)
    and in-memory mode when present on agent.retriever.
    """
    s = settings or getattr(agent, "settings", None) or get_settings()
    current_retriever = getattr(agent, "retriever", None) if agent is not None else None

    embedder = None
    reranker = None
    in_memory = False

    if current_retriever is not None and hasattr(current_retriever, "dense"):
        dense = current_retriever.dense
        embedder = getattr(dense, "embedder", None)
        in_memory = getattr(dense, "_state_file", None) is None
        reranker = getattr(current_retriever, "reranker", None)

    new_retriever = build_retriever(
        settings=s,
        embedder=embedder,
        reranker=reranker,
        in_memory=in_memory,
    )
    if agent is not None:
        agent.retriever = new_retriever

    chunk_count = len(new_retriever.dense.chunks)
    rebuilt = bool(getattr(new_retriever.dense, "rebuilt", False))

    return {
        "chunks": chunk_count,
        "chunk_count": chunk_count,
        "rebuilt": rebuilt,
    }


async def watch_kb(
    agent: Any,
    settings: Settings,
    interval_s: float = 1.0,
    stop_event: asyncio.Event | Any = None,
) -> None:
    """Poll kb_dir for file changes and reload the retriever upon modification."""
    kb_dir = getattr(settings, "kb_dir", Path("data/kb"))
    last_snapshot = kb_snapshot(kb_dir)
    logger.info("KB watcher started for %s (interval=%.2fs)", kb_dir, interval_s)

    while stop_event is None or not stop_event.is_set():
        try:
            await asyncio.sleep(interval_s)
        except asyncio.CancelledError:
            logger.info("KB watcher task cancelled")
            break

        if stop_event is not None and stop_event.is_set():
            break

        current = kb_snapshot(kb_dir)
        if current != last_snapshot:
            logger.info("KB change detected in %s; reloading retriever", kb_dir)
            try:
                info = reload_retriever(agent, settings)
                last_snapshot = current
                logger.info("Retriever reloaded: %s", info)
            except Exception as exc:
                logger.exception("Failed to reload retriever: %s", exc)

    logger.info("KB watcher stopped")
