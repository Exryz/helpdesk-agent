"""Tests for KB filesystem snapshot, hot-reloading, and background watcher."""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from helpdesk.config import Settings, get_settings
from helpdesk.retrieval import build_retriever
from helpdesk.retrieval.models import HashingEmbedder
from helpdesk.retrieval.watcher import kb_snapshot, reload_retriever, watch_kb


@pytest.fixture
def tmp_kb_dir(tmp_path: Path) -> Path:
    kb_path = tmp_path / "kb"
    kb_path.mkdir(parents=True, exist_ok=True)
    src_kb = get_settings().kb_dir

    # Copy 3 articles to tmp kb dir
    src_files = sorted(src_kb.glob("*.md"))[:3]
    for src in src_files:
        shutil.copy(src, kb_path / src.name)
    return kb_path


def test_kb_snapshot(tmp_kb_dir: Path) -> None:
    snap1 = kb_snapshot(tmp_kb_dir)
    assert len(snap1) == 3
    for path_str, mtime in snap1.items():
        assert Path(path_str).exists()
        assert mtime > 0

    # Add a new article
    new_doc = tmp_kb_dir / "KB-999.md"
    new_doc.write_text(
        "---\nid: KB-999\ntitle: Test Doc\ncategory: General\ntags: [test]\n---\n## Section\nContent\n",
        encoding="utf-8",
    )
    snap2 = kb_snapshot(tmp_kb_dir)
    assert len(snap2) == 4
    assert snap2 != snap1
    assert str(new_doc.resolve()) in snap2

    # Delete an article
    new_doc.unlink()
    snap3 = kb_snapshot(tmp_kb_dir)
    assert len(snap3) == 3
    assert snap3 != snap2


def test_reload_retriever_swaps_retriever(tmp_kb_dir: Path) -> None:
    settings = Settings(kb_dir=tmp_kb_dir)
    original_retriever = build_retriever(
        settings=settings,
        in_memory=True,
        embedder=HashingEmbedder(),
        reranker=None,
    )
    agent = SimpleNamespace(retriever=original_retriever, settings=settings)

    info = reload_retriever(agent, settings)
    assert "chunks" in info or "chunk_count" in info
    assert "rebuilt" in info
    assert agent.retriever is not original_retriever
    assert len(agent.retriever.dense.chunks) > 0


@pytest.mark.asyncio
async def test_watch_kb_detects_change_and_reloads(tmp_kb_dir: Path) -> None:
    settings = Settings(kb_dir=tmp_kb_dir)
    retriever = build_retriever(
        settings=settings,
        in_memory=True,
        embedder=HashingEmbedder(),
        reranker=None,
    )
    agent = SimpleNamespace(retriever=retriever, settings=settings)
    original_retriever = agent.retriever
    initial_chunk_count = len(agent.retriever.dense.chunks)

    stop_event = asyncio.Event()
    watch_task = asyncio.create_task(
        watch_kb(agent, settings, interval_s=0.05, stop_event=stop_event)
    )

    # Let watcher take initial snapshot
    await asyncio.sleep(0.08)

    # Add a new article to trigger reload
    new_file = tmp_kb_dir / "KB-TEST-WATCHER.md"
    new_file.write_text(
        "---\nid: KB-WATCHER-999\ntitle: Watcher Test Doc\ncategory: General\ntags: [watcher]\n---\n"
        "## Overview\nThis article was added during watch loop.\n",
        encoding="utf-8",
    )

    # Wait for watcher polling cycle to detect change
    await asyncio.sleep(0.25)
    stop_event.set()
    await watch_task

    # Retriever was swapped and contains new chunks
    assert agent.retriever is not original_retriever
    assert len(agent.retriever.dense.chunks) > initial_chunk_count
