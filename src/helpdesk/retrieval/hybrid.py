"""Hybrid retriever: BM25 + dense, fused with Reciprocal Rank Fusion, optionally reranked."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from helpdesk.retrieval.bm25 import BM25Index
from helpdesk.retrieval.dense import DenseIndex
from helpdesk.retrieval.documents import Chunk
from helpdesk.retrieval.models import Reranker


class Mode(StrEnum):
    BM25 = "bm25"
    DENSE = "dense"
    HYBRID = "hybrid"
    HYBRID_RERANK = "hybrid_rerank"


@dataclass(frozen=True)
class RetrievedChunk:
    chunk: Chunk
    score: float
    rank: int

    def to_dict(self) -> dict[str, object]:
        return {
            "chunk_id": self.chunk.chunk_id,
            "doc_id": self.chunk.doc_id,
            "title": self.chunk.title,
            "section": self.chunk.section,
            "score": round(self.score, 4),
            "text": self.chunk.text,
        }


def reciprocal_rank_fusion(
    rankings: list[list[Chunk]], k: int = 60
) -> list[tuple[Chunk, float]]:
    """Standard RRF: score(d) = sum over rankings of 1 / (k + rank_d)."""
    scores: dict[str, float] = {}
    by_id: dict[str, Chunk] = {}
    for ranking in rankings:
        for rank, chunk in enumerate(ranking, start=1):
            scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0.0) + 1.0 / (k + rank)
            by_id[chunk.chunk_id] = chunk
    return sorted(((by_id[i], s) for i, s in scores.items()), key=lambda x: x[1], reverse=True)


class HybridRetriever:
    def __init__(
        self,
        bm25: BM25Index,
        dense: DenseIndex,
        reranker: Reranker | None = None,
        candidate_k: int = 20,
        default_mode: Mode = Mode.HYBRID_RERANK,
    ):
        self.bm25 = bm25
        self.dense = dense
        self.reranker = reranker
        self.candidate_k = candidate_k
        no_reranker = default_mode == Mode.HYBRID_RERANK and reranker is None
        self.default_mode = Mode.HYBRID if no_reranker else default_mode

    def search(self, query: str, k: int = 4, mode: Mode | str | None = None) -> list[RetrievedChunk]:
        mode = Mode(mode) if mode else self.default_mode
        if mode == Mode.BM25:
            hits = self.bm25.search(query, k)
        elif mode == Mode.DENSE:
            hits = self.dense.search(query, k)
        else:
            fused = reciprocal_rank_fusion(
                [
                    [c for c, _ in self.bm25.search(query, self.candidate_k)],
                    [c for c, _ in self.dense.search(query, self.candidate_k)],
                ]
            )
            if mode == Mode.HYBRID_RERANK:
                if self.reranker is None:
                    raise ValueError("hybrid_rerank mode requires a reranker")
                candidates = [c for c, _ in fused[: self.candidate_k]]
                scores = self.reranker.score(query, [c.embedding_text for c in candidates])
                hits = sorted(zip(candidates, scores, strict=True), key=lambda x: x[1], reverse=True)
            else:
                hits = fused
        return [RetrievedChunk(c, s, r) for r, (c, s) in enumerate(hits[:k], start=1)]
