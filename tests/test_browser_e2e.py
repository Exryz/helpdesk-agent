"""End-to-end browser automation tests running against a real uvicorn server."""

from __future__ import annotations

import socket
import threading
import time
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
import uvicorn

from helpdesk.config import get_settings
from helpdesk.tickets.api import create_app
from helpdesk.tickets.repository import TicketRepository
from helpdesk.tickets.tools import TicketTools

# Skip whole module if playwright is not installed
playwright = pytest.importorskip("playwright")


def _check_chromium_available() -> bool:
    from playwright.sync_api import sync_playwright

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
            return True
    except Exception:
        return False


if not _check_chromium_available():
    pytest.skip("Playwright Chromium browser is not available", allow_module_level=True)

pytestmark = [pytest.mark.browser]


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture(scope="module")
def portal_server(tmp_path_factory: pytest.TempPathFactory) -> Generator[dict[str, Any], None, None]:
    port = _find_free_port()
    db_path = tmp_path_factory.mktemp("e2e_db") / "tickets.db"
    repo = TicketRepository.from_path(db_path, seed=True)
    app = create_app(repo)

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    start_time = time.time()
    while not server.started and (time.time() - start_time) < 10:
        time.sleep(0.05)

    base_url = f"http://127.0.0.1:{port}"
    settings = get_settings()
    old_base_url = settings.portal_base_url
    settings.portal_base_url = base_url

    try:
        yield {"repo": repo, "port": port, "base_url": base_url, "server": server}
    finally:
        settings.portal_base_url = old_base_url
        server.should_exit = True
        thread.join(timeout=5)


@pytest.mark.browser
def test_e2e_scrape_ticket_page_real_chromium(portal_server: dict[str, Any]) -> None:
    """(a) scrape_ticket_page via real Chromium returns TCK-1003 fields."""
    tools = TicketTools(portal_server["repo"])
    result = tools.scrape_ticket_page(url="TCK-1003")

    assert "error" not in result
    assert result["key"] == "TCK-1003"
    assert result["title"] == "VPN disconnects every 10 minutes"
    assert result["status"] == "open"
    assert result["priority"] == "high"
    assert result["category"] == "Network"
    assert result["requester"] == "paul.d"
    assert "AnyConnect drops" in result["description"]
    assert isinstance(result.get("comments"), list)


@pytest.mark.browser
def test_e2e_autofill_preview_screenshot(portal_server: dict[str, Any], tmp_path: Path) -> None:
    """(b) autofill_ticket_form with submit=False saves a screenshot PNG that exists and is >1KB."""
    tools = TicketTools(portal_server["repo"])
    screenshot_file = tmp_path / "autofill_preview.png"

    result = tools.autofill_ticket_form(
        title="Conference room projector not turning on",
        requester="sarah.m",
        priority="medium",
        category="Hardware",
        description="Power LED blinks red repeatedly.",
        url="/portal/new",
        submit=False,
        screenshot_path=str(screenshot_file),
    )

    assert "error" not in result
    assert result["filled"] is True
    assert result["submitted"] is False
    assert result["created_ticket_key"] is None
    assert screenshot_file.exists()
    assert screenshot_file.stat().st_size > 1024


@pytest.mark.browser
def test_e2e_autofill_submit_creates_ticket(portal_server: dict[str, Any]) -> None:
    """(c) submit=True creates a new ticket (verify via repo.search / created_ticket_key)."""
    repo: TicketRepository = portal_server["repo"]
    tools = TicketTools(repo)

    result = tools.autofill_ticket_form(
        title="Laptop battery swollen and trackpad raised",
        requester="clara.b",
        priority="critical",
        category="Hardware",
        description="Battery swelling noticed today.",
        url="/portal/new",
        submit=True,
    )

    assert "error" not in result
    assert result["filled"] is True
    assert result["submitted"] is True
    created_key = result.get("created_ticket_key")
    assert created_key is not None
    assert created_key.startswith("TCK-")

    found = repo.search(requester="clara.b")
    assert len(found) >= 1
    assert any(t.key == created_key for t in found)

    ticket = repo.get(created_key)
    assert ticket.title == "Laptop battery swollen and trackpad raised"
    assert ticket.priority.value == "critical"
    assert ticket.requester == "clara.b"


@pytest.mark.browser
@pytest.mark.asyncio
async def test_e2e_scrape_ticket_inside_running_event_loop(portal_server: dict[str, Any]) -> None:
    """(d) TicketTools.call('scrape_ticket_page', {'url': ...}) works inside a running event loop."""
    tools = TicketTools(portal_server["repo"])
    result = tools.call("scrape_ticket_page", {"url": "/portal/tickets/TCK-1003"})

    assert "error" not in result
    assert result["key"] == "TCK-1003"
    assert result["title"] == "VPN disconnects every 10 minutes"
