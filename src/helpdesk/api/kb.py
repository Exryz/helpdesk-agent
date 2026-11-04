"""Knowledge Base REST API: article listing, full retrieval, search, and live reload."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException, Query

from helpdesk.config import get_settings
from helpdesk.retrieval.documents import load_documents
from helpdesk.retrieval.hybrid import Mode
from helpdesk.retrieval.watcher import reload_retriever


def build_kb_router(app: FastAPI) -> APIRouter:
    router = APIRouter(prefix="/kb", tags=["kb"])

    def _get_kb_dir() -> Path:
        settings = getattr(app.state, "settings", None)
        if settings is not None and hasattr(settings, "kb_dir"):
            return Path(settings.kb_dir)
        return get_settings().kb_dir

    @router.get("")
    def list_articles(
        category: str | None = Query(None, description="Filter articles by category"),
        tag: str | None = Query(None, description="Filter articles by tag"),
    ) -> list[dict[str, Any]]:
        kb_dir = _get_kb_dir()
        try:
            docs = load_documents(kb_dir)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed loading KB articles: {exc}") from exc

        results: list[dict[str, Any]] = []
        for d in docs:
            if category and d.category.lower() != category.strip().lower():
                continue
            if tag and not any(t.lower() == tag.strip().lower() for t in d.tags):
                continue
            results.append(
                {
                    "id": d.id,
                    "title": d.title,
                    "category": d.category,
                    "tags": list(d.tags),
                }
            )
        return results

    @router.get("/search")
    def search_kb(
        q: str = Query(..., description="Search query string"),
        k: int = Query(4, ge=1, le=50, description="Max chunks to return"),
        mode: str | None = Query(None, description="Retrieval mode: bm25, dense, hybrid, hybrid_rerank"),
    ) -> list[dict[str, Any]]:
        agent = getattr(app.state, "agent", None)
        retriever = getattr(agent, "retriever", None)
        if retriever is None:
            raise HTTPException(status_code=503, detail="Retriever not initialized")

        retrieval_mode: Mode | None = None
        if mode:
            try:
                retrieval_mode = Mode(mode)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=f"Invalid retrieval mode: {mode}") from exc

        try:
            hits = retriever.search(query=q, k=k, mode=retrieval_mode)
            return [h.to_dict() if hasattr(h, "to_dict") else h for h in hits]
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Search failed: {exc}") from exc

    @router.get("/{doc_id}")
    def get_article(doc_id: str) -> dict[str, Any]:
        kb_dir = _get_kb_dir()
        try:
            docs = load_documents(kb_dir)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed loading KB articles: {exc}") from exc

        target_id = doc_id.strip().lower()
        for d in docs:
            if d.id.lower() == target_id:
                return {
                    "id": d.id,
                    "title": d.title,
                    "category": d.category,
                    "tags": list(d.tags),
                    "body": d.body,
                    "path": d.path,
                }
        raise HTTPException(status_code=404, detail=f"Article '{doc_id}' not found")

    @router.post("/reload")
    def reload_kb() -> dict[str, Any]:
        settings = getattr(app.state, "settings", None) or get_settings()
        agent = getattr(app.state, "agent", None)
        try:
            return reload_retriever(agent, settings)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"KB reload failed: {exc}") from exc

    return router
