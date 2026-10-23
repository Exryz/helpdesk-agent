"""Dense vector retrieval backed by Qdrant (embedded on-disk, in-memory, or a server)."""

from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from helpdesk.retrieval.documents import Chunk
from helpdesk.retrieval.models import Embedder


def corpus_fingerprint(chunks: list[Chunk], embedder_id: str) -> str:
    h = hashlib.sha256(embedder_id.encode())
    for c in chunks:
        h.update(c.chunk_id.encode())
        h.update(c.embedding_text.encode())
    return h.hexdigest()[:16]


def make_client(path: Path | None = None, url: str | None = None) -> QdrantClient:
    if url:
        return QdrantClient(url=url)
    if path is None:
        return QdrantClient(location=":memory:")
    path.mkdir(parents=True, exist_ok=True)
    return QdrantClient(path=str(path))


class DenseIndex:
    def __init__(
        self,
        chunks: list[Chunk],
        embedder: Embedder,
        client: QdrantClient,
        collection: str = "helpdesk_kb",
        embedder_id: str = "custom",
        state_file: Path | None = None,
    ):
        self.chunks = chunks
        self.embedder = embedder
        self.client = client
        self.collection = collection
        self._by_id = {c.chunk_id: c for c in chunks}
        self._fingerprint = corpus_fingerprint(chunks, embedder_id)
        self._state_file = state_file
        self.rebuilt = False
        if not self._is_current():
            self.build()

    @staticmethod
    def _point_id(chunk_id: str) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id))

    def _is_current(self) -> bool:
        if self._state_file is None or not self._state_file.exists():
            return False
        if not self.client.collection_exists(self.collection):
            return False
        state = json.loads(self._state_file.read_text())
        return bool(state.get("fingerprint") == self._fingerprint)

    def build(self) -> None:
        if self.client.collection_exists(self.collection):
            self.client.delete_collection(self.collection)
        self.client.create_collection(
            self.collection,
            vectors_config=qm.VectorParams(size=self.embedder.dim, distance=qm.Distance.COSINE),
        )
        vectors = self.embedder.embed_documents([c.embedding_text for c in self.chunks])
        self.client.upsert(
            self.collection,
            points=[
                qm.PointStruct(
                    id=self._point_id(c.chunk_id),
                    vector=v,
                    payload={"chunk_id": c.chunk_id, "doc_id": c.doc_id, "title": c.title},
                )
                for c, v in zip(self.chunks, vectors, strict=True)
            ],
        )
        if self._state_file is not None:
            self._state_file.parent.mkdir(parents=True, exist_ok=True)
            self._state_file.write_text(
                json.dumps({"fingerprint": self._fingerprint, "chunks": len(self.chunks)})
            )
        self.rebuilt = True

    def search(self, query: str, k: int = 10) -> list[tuple[Chunk, float]]:
        result = self.client.query_points(
            self.collection, query=self.embedder.embed_query(query), limit=k, with_payload=True
        )
        hits: list[tuple[Chunk, float]] = []
        for p in result.points:
            chunk = self._by_id.get(str((p.payload or {}).get("chunk_id")))
            if chunk is not None:
                hits.append((chunk, float(p.score)))
        return hits
