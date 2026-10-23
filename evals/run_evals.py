"""Evaluation harness: evaluates retrieval modes and full agent workflows."""

from __future__ import annotations

import argparse
import asyncio
import datetime
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from helpdesk.config import Settings, get_settings
from helpdesk.llm import LiteLLMClient
from helpdesk.retrieval import Mode, RetrievedChunk, build_retriever
from helpdesk.retrieval.models import HashingEmbedder, OverlapReranker
from helpdesk.telemetry import Telemetry

# ==============================================================================
# Metric calculation helpers (Pure Python, easily unit-tested)
# ==============================================================================


def hit_at_k(retrieved_doc_ids: Sequence[str], expected_sources: Sequence[str], k: int) -> float:
    """Return 1.0 if any expected source appears in the top-k retrieved docs, else 0.0."""
    if not expected_sources:
        return 0.0
    expected_set = set(expected_sources)
    return 1.0 if any(doc in expected_set for doc in retrieved_doc_ids[:k]) else 0.0


def reciprocal_rank(retrieved_doc_ids: Sequence[str], expected_sources: Sequence[str]) -> float:
    """Return 1 / rank of the first relevant document found (1-indexed), or 0.0."""
    if not expected_sources:
        return 0.0
    expected_set = set(expected_sources)
    for rank, doc in enumerate(retrieved_doc_ids, start=1):
        if doc in expected_set:
            return 1.0 / rank
    return 0.0


def recall_at_k(retrieved_doc_ids: Sequence[str], expected_sources: Sequence[str], k: int) -> float:
    """Return the fraction of expected sources found in the top-k retrieved docs."""
    if not expected_sources:
        return 1.0
    expected_set = set(expected_sources)
    retrieved_set = set(retrieved_doc_ids[:k])
    matched = len(expected_set & retrieved_set)
    return matched / len(expected_set)


def dedupe_doc_ids(chunks: Sequence[RetrievedChunk]) -> list[str]:
    """Extract ordered unique document IDs from retrieved chunks."""
    seen: set[str] = set()
    doc_ids: list[str] = []
    for c in chunks:
        doc_id = c.chunk.doc_id
        if doc_id not in seen:
            seen.add(doc_id)
            doc_ids.append(doc_id)
    return doc_ids


def load_dataset(path: Path | str) -> list[dict[str, Any]]:
    """Load JSONL golden evaluation dataset."""
    rows: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _calc_stats(items: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(items)
    if n == 0:
        return {
            "count": 0,
            "hit_at_1": 0.0,
            "hit_at_3": 0.0,
            "hit_at_4": 0.0,
            "mrr": 0.0,
            "recall_at_4": 0.0,
        }
    return {
        "count": n,
        "hit_at_1": round(sum(x["hit_1"] for x in items) / n, 4),
        "hit_at_3": round(sum(x["hit_3"] for x in items) / n, 4),
        "hit_at_4": round(sum(x["hit_4"] for x in items) / n, 4),
        "mrr": round(sum(x["mrr"] for x in items) / n, 4),
        "recall_at_4": round(sum(x["recall_4"] for x in items) / n, 4),
    }


def aggregate_retrieval(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate per-question retrieval scores into overall and per-category averages."""
    by_category: dict[str, dict[str, Any]] = {}
    categories = sorted({x["category"] for x in results if "category" in x})
    for cat in categories:
        cat_items = [x for x in results if x.get("category") == cat]
        by_category[cat] = _calc_stats(cat_items)

    return {
        "overall": _calc_stats(results),
        "by_category": by_category,
    }


# ==============================================================================
# Evaluation Execution
# ==============================================================================


def evaluate_retrieval(
    dataset: list[dict[str, Any]],
    modes: list[str],
    settings: Settings,
    offline: bool = False,
) -> dict[str, Any]:
    """Run retrieval evaluation across requested modes."""
    # Only evaluate rows that expect at least one KB source
    eval_rows = [r for r in dataset if r.get("expected_sources")]
    if not eval_rows:
        return {}

    if offline:
        retriever = build_retriever(
            settings=settings,
            embedder=HashingEmbedder(dim=256),
            reranker=OverlapReranker(),
            in_memory=True,
        )
    else:
        retriever = build_retriever(settings=settings)

    mode_summaries: dict[str, Any] = {}
    per_question_results: dict[str, list[dict[str, Any]]] = {}

    for mode_str in modes:
        mode = Mode(mode_str)
        row_scores: list[dict[str, Any]] = []

        for row in eval_rows:
            query = row["question"]
            expected = row["expected_sources"]

            # Search with candidate buffer to allow deduplicating chunks into docs
            hits = retriever.search(query=query, k=16, mode=mode)
            retrieved_doc_ids = dedupe_doc_ids(hits)

            h1 = hit_at_k(retrieved_doc_ids, expected, 1)
            h3 = hit_at_k(retrieved_doc_ids, expected, 3)
            h4 = hit_at_k(retrieved_doc_ids, expected, 4)
            mrr = reciprocal_rank(retrieved_doc_ids, expected)
            rec4 = recall_at_k(retrieved_doc_ids, expected, 4)

            row_scores.append(
                {
                    "id": row["id"],
                    "question": query,
                    "category": row.get("category", "unknown"),
                    "expected_sources": expected,
                    "retrieved_doc_ids": retrieved_doc_ids[:4],
                    "hit_1": h1,
                    "hit_3": h3,
                    "hit_4": h4,
                    "mrr": mrr,
                    "recall_4": rec4,
                }
            )

        mode_summaries[mode_str] = aggregate_retrieval(row_scores)
        per_question_results[mode_str] = row_scores

    return {
        "summary": mode_summaries,
        "details": per_question_results,
    }


def has_llm_api_key() -> bool:
    """Check if any standard provider API key is present in the environment."""
    provider_keys = [
        "GEMINI_API_KEY",
        "OPENAI_API_KEY",
        "AZURE_API_KEY",
        "AZURE_OPENAI_API_KEY",
    ]
    return any(bool(os.environ.get(k)) for k in provider_keys)


async def evaluate_agent(
    dataset: list[dict[str, Any]],
    settings: Settings,
    offline: bool = False,
) -> dict[str, Any] | None:
    """Run full agent evaluation across all dataset rows."""
    if offline or not has_llm_api_key():
        reason = "offline mode requested" if offline else "no provider API key set in environment"
        print(f"[INFO] Skipping Agent eval ({reason}).")
        return None

    try:
        from helpdesk.agent.graph import HelpdeskAgent
        from helpdesk.agent.tool_backend import LocalToolBackend
    except ImportError as e:
        print(f"[WARNING] Could not import HelpdeskAgent: {e}. Skipping Agent eval.")
        return None

    from evals.judge_prompts import ANSWER_RELEVANCE_PROMPT, FAITHFULNESS_PROMPT, REFUSAL_PROMPT
    from helpdesk.tickets.repository import TicketRepository
    from helpdesk.tickets.tools import TicketTools

    eval_telemetry = Telemetry(":memory:")
    llm_client = LiteLLMClient(
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        timeout_s=settings.llm_timeout_s,
        telemetry=eval_telemetry,
    )
    judge_client = LiteLLMClient(
        model=settings.resolved_judge_model,
        temperature=0.0,
        timeout_s=settings.llm_timeout_s,
    )
    retriever = build_retriever(settings=settings)

    results: list[dict[str, Any]] = []

    for row in dataset:
        # Create fresh ticket repository for each question to isolate state
        repo = TicketRepository.from_path(":memory:", seed=True)
        tools = LocalToolBackend(TicketTools(repo))

        agent = HelpdeskAgent(
            llm=llm_client,
            retriever=retriever,
            tools=tools,
            settings=settings,
            telemetry=eval_telemetry,
        )

        try:
            res = await agent.run(row["question"])
        except Exception as e:
            err_str = str(e)
            results.append({"id": row["id"], "error": err_str, "category": row.get("category")})
            if "PerDay" in err_str or "GenerateRequestsPerDay" in err_str:
                print("[WARNING] Daily provider quota exhausted; stopping remaining agent eval rows.")
                break
            continue

        # 1. Citation accuracy
        expected_sources = row.get("expected_sources", [])
        cited_doc_ids: set[str] = set()
        for s in res.sources:
            if isinstance(s, dict):
                cited_doc_ids.add(str(s.get("doc_id", "")))
            else:
                cited_doc_ids.add(str(s))

        if expected_sources:
            citation_accurate = 1.0 if bool(set(expected_sources) & cited_doc_ids) else 0.0
        else:
            citation_accurate = 1.0

        # 2. Tool-call accuracy
        expected_tools = set(row.get("expected_tools", []))
        actual_tools = set(res.tools_used)

        if actual_tools == expected_tools:
            tool_accurate = 1.0
        elif "create_ticket" in expected_tools and not actual_tools:
            # Allow create_ticket or an interactive confirmation question
            ans_lower = (res.answer or "").lower()
            confirmation_indicators = ["ticket", "confirm", "create", "proceed", "open"]
            if any(ind in ans_lower for ind in confirmation_indicators) and (
                "?" in ans_lower or "would you like" in ans_lower or "can i" in ans_lower
            ):
                tool_accurate = 1.0
            else:
                tool_accurate = 0.0
        else:
            tool_accurate = 0.0

        # 3. Category-specific LLM judge evaluation
        category = row.get("category", "")
        faithfulness_score: float | None = None
        relevance_score: float | None = None
        refusal_rate: float | None = None

        if category == "out_of_scope":
            judge_prompt = REFUSAL_PROMPT.format(
                question=row["question"],
                answer=res.answer or "",
            )
            try:
                j_resp = await judge_client.chat(
                    [{"role": "user", "content": judge_prompt}],
                    json_mode=True,
                )
                j_json = json.loads(j_resp.content or "{}")
                refusal_rate = 1.0 if j_json.get("refused") is True else 0.0
            except Exception:
                refusal_rate = 0.0
        else:
            # Faithfulness
            context_text = "\n\n".join(
                f"[{s.get('doc_id') or 'KB'}] {s.get('section', '')}\n{s.get('text', '')}"
                if isinstance(s, dict)
                else str(s)
                for s in res.sources
            )
            f_prompt = FAITHFULNESS_PROMPT.format(
                question=row["question"],
                context=context_text or "(No context retrieved)",
                answer=res.answer or "",
            )
            try:
                f_resp = await judge_client.chat(
                    [{"role": "user", "content": f_prompt}],
                    json_mode=True,
                )
                f_json = json.loads(f_resp.content or "{}")
                faithfulness_score = float(f_json.get("score", 0))
            except Exception:
                pass

            # Relevance
            r_prompt = ANSWER_RELEVANCE_PROMPT.format(
                question=row["question"],
                reference_answer=row.get("reference_answer", ""),
                answer=res.answer or "",
            )
            try:
                r_resp = await judge_client.chat(
                    [{"role": "user", "content": r_prompt}],
                    json_mode=True,
                )
                r_json = json.loads(r_resp.content or "{}")
                relevance_score = float(r_json.get("score", 0))
            except Exception:
                pass

        stats = getattr(res, "stats", {}) or {}
        results.append(
            {
                "id": row["id"],
                "category": category,
                "citation_accurate": citation_accurate,
                "tool_accurate": tool_accurate,
                "refusal_rate": refusal_rate,
                "faithfulness_score": faithfulness_score,
                "relevance_score": relevance_score,
                "latency_ms": stats.get("latency_ms", 0.0),
                "cost_usd": stats.get("cost_usd", 0.0),
                "prompt_tokens": stats.get("prompt_tokens", 0),
                "completion_tokens": stats.get("completion_tokens", 0),
            }
        )

    # Aggregate agent metrics
    valid = [r for r in results if "error" not in r]
    n = len(valid)
    if n == 0:
        return {"count": 0, "results": results}

    refusals = [r["refusal_rate"] for r in valid if r["refusal_rate"] is not None]
    faith_scores = [r["faithfulness_score"] for r in valid if r["faithfulness_score"] is not None]
    rel_scores = [r["relevance_score"] for r in valid if r["relevance_score"] is not None]

    summary = {
        "count": n,
        "citation_accuracy": round(sum(r["citation_accurate"] for r in valid) / n, 4),
        "tool_accuracy": round(sum(r["tool_accurate"] for r in valid) / n, 4),
        "refusal_rate": round(sum(refusals) / len(refusals), 4) if refusals else None,
        "faithfulness": round(sum(faith_scores) / len(faith_scores), 2) if faith_scores else None,
        "answer_relevance": round(sum(rel_scores) / len(rel_scores), 2) if rel_scores else None,
        "avg_latency_ms": round(sum(r["latency_ms"] for r in valid) / n, 1),
        "avg_cost_usd": round(sum(r["cost_usd"] for r in valid) / n, 6),
        "avg_tokens": round(sum(r["prompt_tokens"] + r["completion_tokens"] for r in valid) / n, 1),
    }

    return {"summary": summary, "details": results}


# ==============================================================================
# Markdown Report Generation
# ==============================================================================


def generate_markdown_report(
    timestamp: str,
    retrieval_data: dict[str, Any] | None,
    agent_data: dict[str, Any] | None,
    offline: bool,
) -> str:
    exec_mode = "Offline (fakes/in-memory)" if offline else "Production (live models)"
    lines: list[str] = [
        "# Helpdesk Agent Evaluation Report",
        "",
        f"- **Timestamp:** `{timestamp}`",
        f"- **Execution Mode:** `{exec_mode}`",
        "",
    ]

    if retrieval_data and "summary" in retrieval_data:
        lines.extend(
            [
                "## Retrieval Performance Comparison",
                "",
                "| Retrieval Mode | Hit@1 | Hit@3 | Hit@4 | MRR | Recall@4 | Evaluated Rows |",
                "|---|---|---|---|---|---|---|",
            ]
        )
        for mode, data in retrieval_data["summary"].items():
            o = data["overall"]
            lines.append(
                f"| `{mode}` | {o['hit_at_1']:.1%} | {o['hit_at_3']:.1%} | "
                f"{o['hit_at_4']:.1%} | {o['mrr']:.4f} | {o['recall_at_4']:.1%} | "
                f"{o['count']} |"
            )
        lines.append("")

        lines.extend(
            [
                "### Breakdown by Category",
                "",
                "| Retrieval Mode | Category | Count | Hit@1 | Hit@4 | MRR | Recall@4 |",
                "|---|---|---|---|---|---|---|",
            ]
        )
        for mode, data in retrieval_data["summary"].items():
            for cat, cat_data in data["by_category"].items():
                cd = cat_data
                lines.append(
                    f"| `{mode}` | {cat} | {cd['count']} | {cd['hit_at_1']:.1%} | "
                    f"{cd['hit_at_4']:.1%} | {cd['mrr']:.4f} | {cd['recall_at_4']:.1%} |"
                )
        lines.append("")

    if agent_data and agent_data.get("summary"):
        s = agent_data["summary"]
        refusal_str = f"{s['refusal_rate']:.1%}" if s.get("refusal_rate") is not None else "N/A"
        faith_str = f"{s['faithfulness']:.2f} / 5.0" if s.get("faithfulness") is not None else "N/A"
        rel_str = (
            f"{s['answer_relevance']:.2f} / 5.0" if s.get("answer_relevance") is not None else "N/A"
        )

        lines.extend(
            [
                "## Agent Quality & Accuracy",
                "",
                "| Metric | Result |",
                "|---|---|",
                f"| Evaluated Inquiries | {s['count']} |",
                f"| Citation Accuracy | {s['citation_accuracy']:.1%} |",
                f"| Tool-Call Accuracy | {s['tool_accuracy']:.1%} |",
                f"| Out-of-Scope Refusal Rate | {refusal_str} |",
                f"| Faithfulness Score (1-5) | {faith_str} |",
                f"| Answer Relevance Score (1-5) | {rel_str} |",
                f"| Average Latency | {s['avg_latency_ms']:.1f} ms |",
                f"| Average Cost per Inquiry | ${s['avg_cost_usd']:.5f} |",
                f"| Average Tokens per Inquiry | {s['avg_tokens']:.0f} |",
                "",
            ]
        )
    elif agent_data is None:
        lines.extend(
            [
                "## Agent Quality & Accuracy",
                "",
                "*Agent evaluation was skipped (offline mode or no LLM provider key available).* ",
                "",
            ]
        )

    return "\n".join(lines)


# ==============================================================================
# CLI Entrypoint
# ==============================================================================


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate Helpdesk Agent retrieval and end-to-end performance."
    )
    parser.add_argument(
        "--mode",
        choices=["retrieval", "agent", "all"],
        default="all",
        help="Evaluation phase to run (default: all)",
    )
    parser.add_argument(
        "--retrieval-modes",
        default="bm25,dense,hybrid,hybrid_rerank",
        help="Comma-separated retrieval modes to test (default: bm25,dense,hybrid,hybrid_rerank)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of dataset rows to evaluate (useful for smoke tests)",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Run offline using in-memory mock embedder/reranker (no model downloads)",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=None,
        help="Path to evaluation dataset JSONL (default: evals/dataset.jsonl)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output directory for reports (default: evals/results)",
    )
    return parser.parse_args()


async def async_main() -> None:
    args = parse_args()
    settings = get_settings()

    project_root = Path(__file__).resolve().parents[1]
    dataset_path = args.dataset or (project_root / "evals" / "dataset.jsonl")
    out_dir = args.out or (project_root / "evals" / "results")
    out_dir.mkdir(parents=True, exist_ok=True)

    if not dataset_path.exists():
        print(f"[ERROR] Dataset not found at: {dataset_path}")
        sys.exit(1)

    dataset = load_dataset(dataset_path)
    if args.limit:
        dataset = dataset[: args.limit]

    timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d_%H%M%S")
    modes = [m.strip() for m in args.retrieval_modes.split(",") if m.strip()]

    retrieval_data: dict[str, Any] | None = None
    agent_data: dict[str, Any] | None = None

    if args.mode in ("retrieval", "all"):
        n_rows = len(dataset)
        print(f"[INFO] Running retrieval eval ({modes=}, rows={n_rows}, offline={args.offline})...")
        retrieval_data = evaluate_retrieval(dataset, modes, settings, offline=args.offline)

    if args.mode in ("agent", "all"):
        print(f"[INFO] Running agent evaluation (rows={len(dataset)}, offline={args.offline})...")
        agent_data = await evaluate_agent(dataset, settings, offline=args.offline)

    # Save output artifacts
    report_data = {
        "timestamp": timestamp,
        "offline": args.offline,
        "retrieval": retrieval_data,
        "agent": agent_data,
    }

    json_file = out_dir / f"{timestamp}.json"
    json_file.write_text(json.dumps(report_data, indent=2), encoding="utf-8")

    md_report = generate_markdown_report(
        timestamp, retrieval_data, agent_data, offline=args.offline
    )
    latest_md = out_dir / "latest.md"
    latest_md.write_text(md_report, encoding="utf-8")

    print(
        f"[SUCCESS] Wrote evaluation artifacts:\n  - JSON: {json_file}\n  - Markdown: {latest_md}"
    )


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
