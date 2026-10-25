"""Playwright ticket form auto-filler with dry-run screenshot preview support."""

from __future__ import annotations

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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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

    clean = draft.validated()
    plan = build_autofill_plan(clean)
    saved_screenshot: str | None = None

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
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
                await page.click("#submit-ticket")
        finally:
            await browser.close()

    return AutofillResult(
        filled=True,
        submitted=submit,
        fields=clean.to_dict(),
        screenshot_path=saved_screenshot,
    )
