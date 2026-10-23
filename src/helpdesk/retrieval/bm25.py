"""Sparse keyword retrieval with BM25."""

from __future__ import annotations

import re

from rank_bm25 import BM25Okapi

from helpdesk.retrieval.documents import Chunk

_STOPWORDS = frozenset(
    [
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "but",
        "by",
        "can",
        "do",
        "does",
        "for",
        "from",
        "how",
        "i",
        "if",
        "in",
        "is",
        "it",
        "its",
        "my",
        "me",
        "of",
        "on",
        "or",
        "so",
        "that",
        "the",
        "their",
        "there",
        "this",
        "to",
        "was",
        "we",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "will",
        "with",
        "you",
        "your",
        "i'm",
        "im",
        "it's",
        "dont",
        "don't",
        "cant",
        "can't",
        "get",
        "got",
        "keeps",
        "keep",
    ]
)
_TOKEN = re.compile(r"[a-z0-9]+(?:[-'][a-z0-9]+)*")


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in _STOPWORDS]


class BM25Index:
    def __init__(self, chunks: list[Chunk]):
        if not chunks:
            raise ValueError("BM25Index needs at least one chunk")
        self.chunks = chunks
        self._bm25 = BM25Okapi([tokenize(c.embedding_text) for c in chunks])

    def search(self, query: str, k: int = 10) -> list[tuple[Chunk, float]]:
        tokens = tokenize(query)
        if not tokens:
            return []
        scores = self._bm25.get_scores(tokens)
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        return [(self.chunks[i], float(scores[i])) for i in ranked if scores[i] > 0]
