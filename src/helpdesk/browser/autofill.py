"""Playwright ticket form auto-filler with dry-run screenshot preview support."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from helpdesk.tickets.repository import Priority

VALID_PRIORITIES = frozenset(p.value for p in Priority)


@dataclass(frozen=True)
class TicketFormDraft:
    title: str
    requester: str
    priority: str = "medium"
    category: str = "General"
    description: str = ""

    def validated(self) -> TicketFormDraft:
        clean_title = self.title.strip()
        clean_req = self.requester.strip()
        clean_prio = self.priority.strip().lower()
        if not clean_title:
            raise ValueError("Ticket draft title cannot be empty")
        if not clean_req:
            raise ValueError("Ticket draft requester cannot be empty")
        if clean_prio not in VALID_PRIORITIES:
            allowed = sorted(VALID_PRIORITIES)
            raise ValueError(f"Invalid priority {self.priority!r}; expected one of {allowed}")
        return TicketFormDraft(
            title=clean_title,
            requester=clean_req,
            priority=clean_prio,
            category=self.category.strip() or "General",
            description=self.description.strip(),
        )

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class AutofillResult:
    filled: bool
    submitted: bool
    fields: dict[str, str]
    screenshot_path: str | None = None
    created_ticket_key: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def resolve_autofill_url(url: str) -> str:
    """Resolve a relative URL (e.g. '/portal/new') against portal_base_url."""
    cleaned = url.strip()
    if cleaned.startswith(("http://", "https://")):
        return cleaned
    from helpdesk.config import get_settings

    base = get_settings().portal_base_url.rstrip("/")
    if cleaned.startswith("/"):
        return f"{base}{cleaned}"
    return cleaned


def build_autofill_plan(draft: TicketFormDraft) -> list[dict[str, str]]:
    """Build the ordered DOM actions required to populate `#ticket-form`."""
    d = draft.validated()
    return [
        {"action": "fill", "selector": "#title", "value": d.title},
        {"action": "fill", "selector": "#requester", "value": d.requester},
        {"action": "select_option", "selector": "#priority", "value": d.priority},
        {"action": "fill", "selector": "#category", "value": d.category},
        {"action": "fill", "selector": "#description", "value": d.description},
    ]


async def autofill_ticket_form(
    url: str,
    draft: TicketFormDraft,
    submit: bool = False,
    screenshot_path: Path | str | None = None,
    timeout_ms: int = 15000,
) -> AutofillResult:
    """Open a ticket form page in headless Chromium, populate fields, and optionally submit."""
    from playwright.async_api import async_playwright

    target_url = resolve_autofill_url(url)
    clean = draft.validated()
    plan = build_autofill_plan(clean)
    saved_screenshot: str | None = None
    created_ticket_key: str | None = None

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto(target_url, wait_until="domcontentloaded", timeout=timeout_ms)
            await page.wait_for_selector("#ticket-form", timeout=timeout_ms)

            for step in plan:
                if step["action"] == "select_option":
                    await page.select_option(step["selector"], step["value"])
                else:
                    await page.fill(step["selector"], step["value"])

            if screenshot_path is not None:
                target = Path(screenshot_path)
                target.parent.mkdir(parents=True, exist_ok=True)
                await page.screenshot(path=str(target), full_page=True)
                saved_screenshot = str(target)

            if submit:
                async with page.expect_navigation(url=re.compile(r"/portal/tickets/"), timeout=timeout_ms):
                    await page.click("#submit-ticket")
                try:
                    await page.wait_for_selector("#ticket-key", timeout=timeout_ms)
                    el = await page.query_selector("#ticket-key")
                    if el:
                        text = await el.text_content()
                        if text:
                            created_ticket_key = text.strip()
                except Exception:
                    pass
                if not created_ticket_key:
                    m = re.search(r"/portal/tickets/([^/?#]+)", page.url)
                    if m:
                        created_ticket_key = m.group(1)
        finally:
            await browser.close()

    return AutofillResult(
        filled=True,
        submitted=submit,
        fields=clean.to_dict(),
        screenshot_path=saved_screenshot,
        created_ticket_key=created_ticket_key,
    )


def extract_screenshot_paths(tool_calls: list[dict[str, Any]]) -> list[str]:
    """Return existing screenshot file paths produced by browser autofill tool calls."""
    paths: list[str] = []
    for tc in tool_calls:
        res = tc.get("result")
        if isinstance(res, dict):
            raw_path = res.get("screenshot_path")
            if isinstance(raw_path, str) and raw_path and Path(raw_path).is_file():
                paths.append(raw_path)
    return paths

