"""Common test fixtures using deterministic fakes."""

from __future__ import annotations

import pytest

from helpdesk.retrieval import HybridRetriever, build_retriever
from helpdesk.retrieval.models import HashingEmbedder, OverlapReranker
from helpdesk.tickets.repository import TicketRepository
from helpdesk.tickets.tools import TicketTools


@pytest.fixture
def fake_retriever() -> HybridRetriever:
    return build_retriever(
        in_memory=True,
        embedder=HashingEmbedder(),
        reranker=OverlapReranker(),
    )


@pytest.fixture
def repo() -> TicketRepository:
    return TicketRepository.from_path(":memory:")


@pytest.fixture
def local_tools(repo: TicketRepository) -> TicketTools:
    return TicketTools(repo)
