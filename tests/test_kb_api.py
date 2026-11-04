"""Tests for the Knowledge Base REST API endpoints."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from helpdesk.api.kb import build_kb_router
from helpdesk.config import get_settings
from helpdesk.retrieval.hybrid import HybridRetriever


@pytest.fixture
def kb_client(fake_retriever: HybridRetriever) -> TestClient:
    app = FastAPI()
    app.state.agent = SimpleNamespace(retriever=fake_retriever)
    app.state.settings = get_settings()
    app.include_router(build_kb_router(app))
    return TestClient(app)


def test_list_articles(kb_client: TestClient) -> None:
    response = kb_client.get("/kb")
    assert response.status_code == 200
    articles = response.json()
    assert isinstance(articles, list)
    assert len(articles) > 0

    first = articles[0]
    for key in ("id", "title", "category", "tags"):
        assert key in first


def test_list_articles_filter_category_and_tag(kb_client: TestClient) -> None:
    response = kb_client.get("/kb")
    assert response.status_code == 200
    articles = response.json()
    cat = articles[0]["category"]
    tag = articles[0]["tags"][0] if articles[0]["tags"] else None

    # Filter by category
    resp_cat = kb_client.get(f"/kb?category={cat}")
    assert resp_cat.status_code == 200
    filtered_cat = resp_cat.json()
    assert all(a["category"].lower() == cat.lower() for a in filtered_cat)
    assert len(filtered_cat) > 0

    # Filter by non-existent category
    resp_none = kb_client.get("/kb?category=NonExistentCategoryXYZ")
    assert resp_none.status_code == 200
    assert resp_none.json() == []

    # Filter by tag
    if tag:
        resp_tag = kb_client.get(f"/kb?tag={tag}")
        assert resp_tag.status_code == 200
        filtered_tag = resp_tag.json()
        assert all(any(t.lower() == tag.lower() for t in a["tags"]) for a in filtered_tag)
        assert len(filtered_tag) > 0


def test_get_article_found_and_case_insensitive(kb_client: TestClient) -> None:
    list_resp = kb_client.get("/kb")
    first_id = list_resp.json()[0]["id"]

    # Exact ID
    resp = kb_client.get(f"/kb/{first_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == first_id
    assert "body" in data
    assert "title" in data
    assert "category" in data
    assert "tags" in data
    assert "path" in data

    # Case-insensitive ID
    lower_id = first_id.lower()
    resp_lower = kb_client.get(f"/kb/{lower_id}")
    assert resp_lower.status_code == 200
    assert resp_lower.json()["id"] == first_id


def test_get_article_not_found(kb_client: TestClient) -> None:
    resp = kb_client.get("/kb/non-existent-article-id-999")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_search_kb_modes_and_k(kb_client: TestClient) -> None:
    # Default search
    resp = kb_client.get("/kb/search?q=vpn")
    assert resp.status_code == 200
    results = resp.json()
    assert isinstance(results, list)
    assert len(results) > 0

    first = results[0]
    for key in ("chunk_id", "doc_id", "title", "section", "score", "text"):
        assert key in first

    # Limit k=2
    resp_k = kb_client.get("/kb/search?q=vpn&k=2")
    assert resp_k.status_code == 200
    assert len(resp_k.json()) <= 2

    # Mode bm25
    resp_bm25 = kb_client.get("/kb/search?q=vpn&mode=bm25")
    assert resp_bm25.status_code == 200
    assert len(resp_bm25.json()) > 0

    # Invalid mode
    resp_bad = kb_client.get("/kb/search?q=vpn&mode=unknown_mode")
    assert resp_bad.status_code == 400
    assert "invalid retrieval mode" in resp_bad.json()["detail"].lower()


def test_reload_kb(kb_client: TestClient) -> None:
    resp = kb_client.post("/kb/reload")
    assert resp.status_code == 200
    data = resp.json()
    assert "chunks" in data or "chunk_count" in data
    assert "rebuilt" in data
    assert isinstance(data["rebuilt"], bool)
    assert data.get("chunks", data.get("chunk_count", 0)) > 0
