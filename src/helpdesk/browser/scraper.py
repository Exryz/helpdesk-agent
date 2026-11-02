"""Playwright ticket page scraper and HTML parser for legacy portal pages."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from html.parser import HTMLParser
from typing import Any


@dataclass(frozen=True)
class ScrapedTicket:
    key: str
    title: str
    status: str
    priority: str
    category: str
    requester: str
    description: str
    comments: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class _PortalTicketParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.fields: dict[str, str] = {}
        self.comments: list[dict[str, str]] = []
        self._active_field: str | None = None
        self._buf: list[str] = []
        self._in_comment_author: str | None = None
        self._in_comment_body: bool = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {k: (v or "") for k, v in attrs}
        if "data-field" in attr_map:
            self._active_field = attr_map["data-field"]
            self._buf = []
        elif tag == "li" and "comment" in attr_map.get("class", ""):
            self._in_comment_author = attr_map.get("data-author", "")
        elif (
            tag == "span"
            and "comment-body" in attr_map.get("class", "")
            and self._in_comment_author is not None
        ):
            self._in_comment_body = True
            self._buf = []

    def handle_data(self, data: str) -> None:
        if self._active_field is not None or self._in_comment_body:
            self._buf.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._active_field is not None and tag in {"h1", "dd", "section"}:
            self.fields[self._active_field] = "".join(self._buf).strip()
            self._active_field = None
            self._buf = []
        elif self._in_comment_body and tag == "span":
            self.comments.append(
                {
                    "author": self._in_comment_author or "",
                    "body": "".join(self._buf).strip(),
                }
            )
            self._in_comment_body = False
            self._buf = []
        elif tag == "li" and self._in_comment_author is not None:
            self._in_comment_author = None


def parse_ticket_html(raw_html: str) -> ScrapedTicket:
    """Extract structured ticket fields from a `/portal/tickets/{key}` HTML document."""
    parser = _PortalTicketParser()
    parser.feed(raw_html)
    f = parser.fields
    if not f.get("key") or not f.get("title"):
        raise ValueError("HTML does not contain a valid #ticket-detail structure")
    return ScrapedTicket(
        key=f.get("key", ""),
        title=f.get("title", ""),
        status=f.get("status", ""),
        priority=f.get("priority", ""),
        category=f.get("category", ""),
        requester=f.get("requester", ""),
        description=f.get("description", ""),
        comments=parser.comments,
    )


def resolve_scrape_url(url: str) -> str:
    """Resolve a portal ticket URL, relative path, or bare ticket key against portal_base_url."""
    cleaned = url.strip()
    if cleaned.startswith(("http://", "https://")):
        return cleaned
    from helpdesk.config import get_settings

    base = get_settings().portal_base_url.rstrip("/")
    if cleaned.startswith("/"):
        return f"{base}{cleaned}"
    return f"{base}/portal/tickets/{cleaned}"


async def scrape_ticket_page(url: str, timeout_ms: int = 15000) -> ScrapedTicket:
    """Navigate to `url` with headless Chromium via Playwright and extract ticket details."""
    from playwright.async_api import async_playwright

    target_url = resolve_scrape_url(url)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto(target_url, wait_until="domcontentloaded", timeout=timeout_ms)
            await page.wait_for_selector("#ticket-detail", timeout=timeout_ms)
            html_content = await page.content()
        finally:
            await browser.close()

    return parse_ticket_html(html_content)
