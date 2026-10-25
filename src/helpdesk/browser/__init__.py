"""Browser automation utilities for scraping legacy ticket pages and auto-filling forms."""

from helpdesk.browser.scraper import ScrapedTicket, parse_ticket_html, scrape_ticket_page

__all__ = ["ScrapedTicket", "parse_ticket_html", "scrape_ticket_page"]
