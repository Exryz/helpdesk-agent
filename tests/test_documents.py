"""Unit tests for knowledge base document parsing and chunking."""

from __future__ import annotations

from pathlib import Path

import pytest

from helpdesk.config import get_settings
from helpdesk.retrieval.documents import (
    Document,
    chunk_document,
    load_chunks,
    load_documents,
    parse_document,
)


def test_parse_document_valid(tmp_path: Path) -> None:
    doc_file = tmp_path / "valid.md"
    doc_file.write_text(
        """---
id: KB-999
title: Sample Test Document
category: Testing
tags: [unit, test, docs]
---

# Sample Test Document

This is the overview paragraph.

## First Steps
Follow step 1, step 2, step 3.
""",
        encoding="utf-8",
    )

    doc = parse_document(doc_file)
    assert doc.id == "KB-999"
    assert doc.title == "Sample Test Document"
    assert doc.category == "Testing"
    assert doc.tags == ("unit", "test", "docs")
    assert "First Steps" in doc.body
    assert doc.path == str(doc_file)


def test_parse_document_missing_frontmatter(tmp_path: Path) -> None:
    doc_file = tmp_path / "invalid.md"
    doc_file.write_text("# No Frontmatter\nJust body content.", encoding="utf-8")
    with pytest.raises(ValueError, match="missing YAML frontmatter"):
        parse_document(doc_file)


def test_parse_document_missing_required_keys(tmp_path: Path) -> None:
    doc_file = tmp_path / "missing_title.md"
    doc_file.write_text("---\nid: KB-123\n---\nBody", encoding="utf-8")
    with pytest.raises(ValueError, match="frontmatter missing 'title'"):
        parse_document(doc_file)


def test_chunking_overview_and_sections() -> None:
    doc = Document(
        id="KB-100",
        title="Wi-Fi Troubleshooting",
        category="Network",
        tags=("wifi", "network"),
        body="""Intro overview paragraph detailing Wi-Fi basics.

## Symptom 1: Cannot Connect
Make sure Wi-Fi toggle is ON in system tray. Verify airplane mode is disabled.
This section has enough characters to exceed minimum threshold without being merged into others.

## Symptom 2: Password Rejected
Confirm caps lock is off. Re-type the enterprise WPA2 password.
Ensure your network profile is updated and sync credentials with Okta portal.
""",
        path="/fake/path",
    )

    chunks = chunk_document(doc, max_chars=500, min_chars=50)
    assert len(chunks) >= 2
    assert chunks[0].doc_id == "KB-100"
    assert chunks[0].title == "Wi-Fi Troubleshooting"
    assert chunks[0].embedding_text.startswith("Wi-Fi Troubleshooting - ")


def test_chunking_merges_short_sections() -> None:
    doc = Document(
        id="KB-101",
        title="Printer Setup",
        category="Hardware",
        tags=("printer",),
        body="""
## Short Section
Short.

## Main Instructions
Detailed instructions for setting up the PaperCut queue on Windows 11 with badge release.
This section contains enough text to satisfy the minimum length threshold.
""",
        path="/fake/path",
    )

    chunks = chunk_document(doc, min_chars=100)
    # The short section should have been merged into the next section
    assert len(chunks) == 1
    assert "Short Section" in chunks[0].section
    assert "Main Instructions" in chunks[0].section


def test_load_all_30_kb_articles() -> None:
    settings = get_settings()
    docs = load_documents(settings.kb_dir)

    assert len(docs) == 30, f"Expected 30 KB articles, found {len(docs)}"

    doc_ids = [d.id for d in docs]
    assert len(set(doc_ids)) == 30, "Document IDs must be unique"

    for i in range(1, 31):
        expected_id = f"KB-{i:03d}"
        assert expected_id in doc_ids, f"Missing article {expected_id}"

    for doc in docs:
        assert doc.title.strip(), f"Empty title in {doc.id}"
        assert doc.category.strip(), f"Empty category in {doc.id}"
        assert len(doc.body.strip()) > 50, f"Body too short in {doc.id}"

    chunks = load_chunks(settings.kb_dir)
    assert len(chunks) >= 30
    for chunk in chunks:
        assert chunk.chunk_id.startswith(f"{chunk.doc_id}#")
        assert chunk.embedding_text.strip()
