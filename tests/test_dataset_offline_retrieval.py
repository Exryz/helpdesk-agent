"""Smoke test running offline retrieval evaluation across all modes with zero network calls."""

from __future__ import annotations

from evals.run_evals import evaluate_retrieval, load_dataset
from helpdesk.config import get_settings


def test_offline_retrieval_smoke() -> None:
    settings = get_settings()
    dataset_path = settings.kb_dir.parents[1] / "evals" / "dataset.jsonl"
    dataset = load_dataset(dataset_path)[:6]

    modes = ["bm25", "dense", "hybrid", "hybrid_rerank"]
    result = evaluate_retrieval(
        dataset=dataset,
        modes=modes,
        settings=settings,
        offline=True,
    )

    assert "summary" in result
    summary = result["summary"]

    for mode in modes:
        assert mode in summary
        stats = summary[mode]["overall"]
        assert stats["count"] > 0
        assert 0.0 <= stats["hit_at_1"] <= 1.0
        assert 0.0 <= stats["hit_at_3"] <= 1.0
        assert 0.0 <= stats["hit_at_4"] <= 1.0
        assert 0.0 <= stats["mrr"] <= 1.0
        assert 0.0 <= stats["recall_at_4"] <= 1.0
