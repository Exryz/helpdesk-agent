"""Unit tests for retrieval components: BM25, DenseIndex, RRF, and HybridRetriever."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from helpdesk.retrieval.bm25 import BM25Index, tokenize
from helpdesk.retrieval.dense import DenseIndex, corpus_fingerprint, make_client
from helpdesk.retrieval.documents import Chunk
from helpdesk.retrieval.hybrid import HybridRetriever, Mode, reciprocal_rank_fusion
from helpdesk.retrieval.models import HashingEmbedder, OverlapReranker


def _sample_chunks() -> list[Chunk]:
    return [
        Chunk(
            chunk_id="KB-001#1",
            doc_id="KB-001",
            title="VPN Setup",
            section="Troubleshooting",
            text="AnyConnect connection drops after 30 minutes of idle inactivity timeout.",
        ),
        Chunk(
            chunk_id="KB-002#1",
            doc_id="KB-002",
            title="Certificate Errors",
            section="Intune Sync",
            text="Certificate validation failure on corporate VPN. Sync certificate.",
        ),
        Chunk(
            chunk_id="KB-003#1",
            doc_id="KB-003",
            title="Guest Wi-Fi",
            section="Visitor Access",
            text="Visitors can connect to Northwind-Guest Wi-Fi portal for 24-hour guest pass.",
        ),
    ]


def test_tokenize() -> None:
    tokens = tokenize("How do I fix the Cisco AnyConnect VPN connection on Windows 11?")
    assert "cisco" in tokens
    assert "anyconnect" in tokens
    assert "vpn" in tokens
    # Stopwords should be excluded
    assert "how" not in tokens
    assert "do" not in tokens
    assert "i" not in tokens


def test_bm25_search() -> None:
    chunks = _sample_chunks()
    bm25 = BM25Index(chunks)

    # Empty chunks raises error
    with pytest.raises(ValueError, match="at least one chunk"):
        BM25Index([])

    # Empty query returns empty list
    assert bm25.search("") == []

    # Query with matching terms
    hits = bm25.search("AnyConnect idle timeout", k=2)
    assert len(hits) > 0
    assert hits[0][0].doc_id == "KB-001"
    assert hits[0][1] > 0.0


def test_reciprocal_rank_fusion() -> None:
    chunks = _sample_chunks()
    # List 1: chunk 0, chunk 1
    # List 2: chunk 1, chunk 2
    ranking1 = [chunks[0], chunks[1]]
    ranking2 = [chunks[1], chunks[2]]

    fused = reciprocal_rank_fusion([ranking1, ranking2], k=60)
    assert len(fused) == 3
    # chunks[1] appeared at rank 2 in list 1 and rank 1 in list 2 -> total score highest
    top_chunk, score = fused[0]
    assert top_chunk.chunk_id == "KB-002#1"
    assert score > 0


def test_dense_index_in_memory() -> None:
    chunks = _sample_chunks()
    client = make_client(None)
    embedder = HashingEmbedder(dim=128)

    dense = DenseIndex(chunks, embedder, client, collection="test_col")
    assert dense.rebuilt is True

    hits = dense.search("Guest visitor wireless access", k=2)
    assert len(hits) > 0
    # KB-003 mentions Guest, visitor, wireless
    assert hits[0][0].doc_id == "KB-003"


def test_dense_index_fingerprint_and_caching(tmp_path: Path) -> None:
    chunks = _sample_chunks()
    client = make_client(tmp_path / "qdrant")
    state_file = tmp_path / "index_state.json"
    embedder = HashingEmbedder(dim=64)

    fp1 = corpus_fingerprint(chunks, "HashingEmbedder")
    assert isinstance(fp1, str) and len(fp1) == 16

    # First run builds the index
    idx1 = DenseIndex(
        chunks,
        embedder,
        client,
        collection="test_cache",
        embedder_id="HashingEmbedder",
        state_file=state_file,
    )
    assert idx1.rebuilt is True
    assert state_file.exists()

    state_data = json.loads(state_file.read_text())
    assert state_data["fingerprint"] == fp1

    # Second run with same data skips rebuild
    idx2 = DenseIndex(
        chunks,
        embedder,
        client,
        collection="test_cache",
        embedder_id="HashingEmbedder",
        state_file=state_file,
    )
    assert idx2.rebuilt is False


def test_hybrid_retriever_modes() -> None:
    chunks = _sample_chunks()
    client = make_client(None)
    embedder = HashingEmbedder(dim=128)
    reranker = OverlapReranker()
    bm25 = BM25Index(chunks)
    dense = DenseIndex(chunks, embedder, client, collection="hybrid_test")

    retriever = HybridRetriever(bm25, dense, reranker=reranker, candidate_k=3)

    # 1. Mode BM25
    bm25_hits = retriever.search("AnyConnect timeout", k=2, mode=Mode.BM25)
    assert len(bm25_hits) > 0
    assert bm25_hits[0].chunk.doc_id == "KB-001"

    # 2. Mode Dense
    dense_hits = retriever.search("visitor wireless", k=2, mode=Mode.DENSE)
    assert len(dense_hits) > 0

    # 3. Mode Hybrid
    hybrid_hits = retriever.search("certificate failure", k=2, mode=Mode.HYBRID)
    assert len(hybrid_hits) > 0
    assert hybrid_hits[0].chunk.doc_id == "KB-002"

    # 4. Mode Hybrid Rerank
    rerank_hits = retriever.search(
        "certificate validation failure Intune", k=2, mode=Mode.HYBRID_RERANK
    )
    assert len(rerank_hits) > 0
    assert rerank_hits[0].chunk.doc_id == "KB-002"

    # 5. Missing reranker raises error on HYBRID_RERANK
    no_rerank_retriever = HybridRetriever(bm25, dense, reranker=None)
    with pytest.raises(ValueError, match="hybrid_rerank mode requires a reranker"):
        no_rerank_retriever.search("test", mode=Mode.HYBRID_RERANK)
