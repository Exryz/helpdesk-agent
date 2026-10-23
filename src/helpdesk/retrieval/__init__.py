"""Retrieval: chunking, BM25, dense (Qdrant), RRF fusion and cross-encoder reranking."""

from __future__ import annotations

from helpdesk.config import Settings, get_settings
from helpdesk.retrieval.bm25 import BM25Index
from helpdesk.retrieval.dense import DenseIndex, make_client
from helpdesk.retrieval.documents import Chunk, load_chunks
from helpdesk.retrieval.hybrid import HybridRetriever, Mode, RetrievedChunk
from helpdesk.retrieval.models import Embedder, Reranker

__all__ = ["Chunk", "HybridRetriever", "Mode", "RetrievedChunk", "build_retriever"]


def build_retriever(
    settings: Settings | None = None,
    embedder: Embedder | None = None,
    reranker: Reranker | None = None,
    in_memory: bool = False,
) -> HybridRetriever:
    """Build the production retriever from settings (models are loaded lazily here)."""
    s = settings or get_settings()
    chunks = load_chunks(s.kb_dir, max_chars=s.chunk_max_chars)
    embedder_id = s.embedding_model
    if embedder is None:
        from helpdesk.retrieval.models import FastEmbedEmbedder

        embedder = FastEmbedEmbedder(s.embedding_model)
    else:
        embedder_id = type(embedder).__name__
    if reranker is None and s.use_reranker:
        from helpdesk.retrieval.models import FastEmbedReranker

        reranker = FastEmbedReranker(s.reranker_model)

    client = make_client(None if in_memory else s.qdrant_path, None if in_memory else s.qdrant_url)
    state_file = None if in_memory else s.qdrant_path.parent / "index_state.json"
    dense = DenseIndex(
        chunks, embedder, client, s.collection, embedder_id=embedder_id, state_file=state_file
    )
    return HybridRetriever(BM25Index(chunks), dense, reranker, candidate_k=s.candidate_k)
