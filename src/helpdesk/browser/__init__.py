"""Browser automation utilities for scraping legacy ticket pages and auto-filling forms."""

from helpdesk.browser.autofill import (
    AutofillResult,
    TicketFormDraft,
    autofill_ticket_form,
    build_autofill_plan,
)
from helpdesk.browser.scraper import ScrapedTicket, parse_ticket_html, scrape_ticket_page

__all__ = [
    "AutofillResult",
    "ScrapedTicket",
    "TicketFormDraft",
    "autofill_ticket_form",
    "build_autofill_plan",
    "parse_ticket_html",
    "scrape_ticket_page",
]
