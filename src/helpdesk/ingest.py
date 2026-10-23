"""CLI command to build or rebuild the Knowledge Base retrieval index."""

from __future__ import annotations

import argparse
import sys

from helpdesk.config import get_settings
from helpdesk.retrieval import build_retriever


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Ingest Knowledge Base documents into the hybrid vector index."
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Delete index_state.json and force rebuilding the dense index.",
    )
    parser.add_argument(
        "--query",
        type=str,
        default=None,
        help="Optional test query to run against the index after ingestion.",
    )
    args = parser.parse_args(argv)

    settings = get_settings()
    state_file = settings.qdrant_path.parent / "index_state.json"
    if args.rebuild and state_file.exists():
        state_file.unlink()
        print(f"Removed {state_file} to force rebuild.")

    print(f"Building retriever from {settings.kb_dir}...")
    retriever = build_retriever(settings)
    chunk_count = len(retriever.dense.chunks)
    rebuilt = getattr(retriever.dense, "rebuilt", False)

    print(f"Index status: {'Rebuilt' if rebuilt else 'Up to date'}")
    print(f"Total chunks indexed: {chunk_count}")

    if args.query:
        print(f"\nRunning test query: {args.query!r}")
        results = retriever.search(args.query, k=settings.top_k)
        for i, hit in enumerate(results, 1):
            print(
                f"  {i}. [{hit.chunk.doc_id}] {hit.chunk.title} - {hit.chunk.section} "
                f"(score: {hit.score:.4f})"
            )


if __name__ == "__main__":
    main(sys.argv[1:])
