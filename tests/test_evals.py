"""Unit tests for evaluation metrics and validation of the golden evaluation dataset."""

from __future__ import annotations

import pytest

from evals.run_evals import (
    aggregate_retrieval,
    hit_at_k,
    load_dataset,
    recall_at_k,
    reciprocal_rank,
)
from helpdesk.config import get_settings
from helpdesk.retrieval.documents import load_documents
from helpdesk.tickets.tools import TOOL_NAMES


def test_metric_hit_at_k() -> None:
    retrieved = ["KB-001", "KB-002", "KB-003", "KB-004"]

    assert hit_at_k(retrieved, ["KB-001"], 1) == 1.0
    assert hit_at_k(retrieved, ["KB-002"], 1) == 0.0
    assert hit_at_k(retrieved, ["KB-002"], 3) == 1.0
    assert hit_at_k(retrieved, ["KB-005"], 4) == 0.0
    # Empty expected
    assert hit_at_k(retrieved, [], 4) == 0.0


def test_metric_reciprocal_rank() -> None:
    retrieved = ["KB-001", "KB-002", "KB-003", "KB-004"]

    assert reciprocal_rank(retrieved, ["KB-001"]) == 1.0
    assert pytest.approx(reciprocal_rank(retrieved, ["KB-003"])) == 1.0 / 3.0
    assert reciprocal_rank(retrieved, ["KB-999"]) == 0.0
    assert reciprocal_rank(retrieved, []) == 0.0


def test_metric_recall_at_k() -> None:
    retrieved = ["KB-001", "KB-002", "KB-003", "KB-004"]

    # Both present in top 2
    assert recall_at_k(retrieved, ["KB-001", "KB-002"], 2) == 1.0
    # Only 1 of 2 present in top 1
    assert recall_at_k(retrieved, ["KB-001", "KB-002"], 1) == 0.5
    # None present
    assert recall_at_k(retrieved, ["KB-009"], 4) == 0.0
    # Empty expected
    assert recall_at_k(retrieved, [], 4) == 1.0


def test_aggregate_retrieval() -> None:
    records = [
        {
            "category": "kb_answer",
            "hit_1": 1.0,
            "hit_3": 1.0,
            "hit_4": 1.0,
            "mrr": 1.0,
            "recall_4": 1.0,
        },
        {
            "category": "kb_answer",
            "hit_1": 0.0,
            "hit_3": 1.0,
            "hit_4": 1.0,
            "mrr": 0.5,
            "recall_4": 1.0,
        },
        {
            "category": "ticket_action",
            "hit_1": 1.0,
            "hit_3": 1.0,
            "hit_4": 1.0,
            "mrr": 1.0,
            "recall_4": 1.0,
        },
    ]

    agg = aggregate_retrieval(records)
    overall = agg["overall"]
    assert overall["count"] == 3
    assert pytest.approx(overall["hit_at_1"]) == round(2.0 / 3.0, 4)
    assert overall["hit_at_4"] == 1.0

    by_cat = agg["by_category"]
    assert "kb_answer" in by_cat
    assert by_cat["kb_answer"]["count"] == 2
    assert by_cat["kb_answer"]["hit_at_1"] == 0.5
    assert by_cat["ticket_action"]["count"] == 1
    assert by_cat["ticket_action"]["hit_at_1"] == 1.0


def test_dataset_schema_and_integrity() -> None:
    settings = get_settings()
    dataset_path = settings.kb_dir.parents[1] / "evals" / "dataset.jsonl"
    rows = load_dataset(dataset_path)

    # 1. Exactly 50 rows
    assert len(rows) == 50, f"Expected 50 rows, got {len(rows)}"

    # 2. Collect all valid KB doc IDs from data/kb
    valid_kb_ids = {doc.id for doc in load_documents(settings.kb_dir)}
    valid_categories = {"kb_answer", "ticket_action", "out_of_scope"}

    for idx, row in enumerate(rows, start=1):
        # Validate required fields
        for field in (
            "id",
            "question",
            "expected_sources",
            "reference_answer",
            "expected_tools",
            "category",
        ):
            assert field in row, f"Row {idx} ({row.get('id')}) missing field '{field}'"

        assert isinstance(row["id"], str) and row["id"].strip()
        assert isinstance(row["question"], str) and row["question"].strip()
        assert isinstance(row["expected_sources"], list)
        assert isinstance(row["expected_tools"], list)
        assert row["category"] in valid_categories, (
            f"Invalid category '{row['category']}' in row {idx}"
        )

        # Expected sources must exist in KB
        for source in row["expected_sources"]:
            assert source in valid_kb_ids, f"Row {row['id']} references unknown source '{source}'"

        # Expected tools must be a subset of TOOL_NAMES
        for tool in row["expected_tools"]:
            assert tool in TOOL_NAMES, f"Row {row['id']} references unknown tool '{tool}'"
