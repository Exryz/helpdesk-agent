"""HTML web portal routes for legacy ticket viewing and form submission.

Provides lightweight HTML pages (`/portal/tickets/{key}` and `/portal/new`) so browser
automation tools (such as Playwright) can scrape ticket details and auto-fill ticket forms.
"""

from __future__ import annotations

import html

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from helpdesk.tickets.repository import (
    Priority,
    TicketNotFound,
    TicketRepository,
)


def _esc(val: object) -> str:
    return html.escape(str(val))


def build_portal_router(repo: TicketRepository) -> APIRouter:
    router = APIRouter(prefix="/portal", tags=["portal"])

    @router.get("/tickets/{key}", response_class=HTMLResponse)
    def portal_ticket_detail(key: str) -> HTMLResponse:
        try:
            t = repo.get(key)
            comments = repo.comments(key)
        except TicketNotFound as e:
            raise HTTPException(status_code=404, detail=str(e)) from e

        comment_items = "".join(
            f'<li class="comment" data-author="{_esc(c.author)}">'
            f"<strong>{_esc(c.author)}</strong>: <span class=\"comment-body\">{_esc(c.body)}</span>"
            f"</li>"
            for c in comments
        )
        body = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>{_esc(t.key)} - {_esc(t.title)}</title></head>
<body>
  <main id="ticket-detail" data-ticket-key="{_esc(t.key)}">
    <h1 id="ticket-title" data-field="title">{_esc(t.title)}</h1>
    <dl>
      <dt>Key</dt><dd id="ticket-key" data-field="key">{_esc(t.key)}</dd>
      <dt>Status</dt><dd id="ticket-status" data-field="status">{_esc(t.status)}</dd>
      <dt>Priority</dt><dd id="ticket-priority" data-field="priority">{_esc(t.priority)}</dd>
      <dt>Category</dt><dd id="ticket-category" data-field="category">{_esc(t.category)}</dd>
      <dt>Requester</dt><dd id="ticket-requester" data-field="requester">{_esc(t.requester)}</dd>
    </dl>
    <section id="ticket-description" data-field="description">{_esc(t.description)}</section>
    <ul id="ticket-comments">{comment_items}</ul>
  </main>
</body>
</html>"""
        return HTMLResponse(content=body)

    @router.get("/new", response_class=HTMLResponse)
    def portal_new_ticket_form() -> HTMLResponse:
        options = "".join(
            f'<option value="{_esc(p.value)}">{_esc(p.value)}</option>' for p in Priority
        )
        body = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>New Support Ticket - Northwind IT Portal</title></head>
<body>
  <main>
    <h1>Submit a Support Ticket</h1>
    <form id="ticket-form" action="/tickets" method="post">
      <label for="title">Title</label>
      <input id="title" name="title" type="text" required />
      <label for="requester">Requester</label>
      <input id="requester" name="requester" type="text" required />
      <label for="priority">Priority</label>
      <select id="priority" name="priority">{options}</select>
      <label for="category">Category</label>
      <input id="category" name="category" type="text" value="General" />
      <label for="description">Description</label>
      <textarea id="description" name="description"></textarea>
      <button id="submit-ticket" type="submit">Create Ticket</button>
    </form>
  </main>
</body>
</html>"""
        return HTMLResponse(content=body)

    return router
