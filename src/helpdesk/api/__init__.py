"""FastAPI REST API for Helpdesk Agent."""

from __future__ import annotations

from helpdesk.api.main import app_factory, create_app

__all__ = ["app_factory", "create_app"]
