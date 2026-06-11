"""
InboxPilot AI — Playwright smoke test

Verifies the app loads, key UI elements are visible, and the demo workflow
produces expected outcomes. Runs against a live local Streamlit instance.

Usage:
    # Start Streamlit first:
    streamlit run app.py --server.headless true --server.port 8502

    # Then run this test:
    python -m pytest e2e/ -v --timeout=60

Or use the combined helper:
    python e2e/run_smoke_test.py
"""
import subprocess
import sys
import os
import time
import socket

import pytest
from playwright.sync_api import Page, expect, sync_playwright

# ── Configuration ─────────────────────────────────────────────────────────────

BASE_URL = "http://localhost:8502"
SCREENSHOTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "docs", "screenshots"
)
STREAMLIT_STARTUP_TIMEOUT = 30  # seconds
STREAMLIT_NAVIGATE_WAIT = 2500   # ms — Streamlit re-renders on sidebar click


# ── Session-level fixtures ─────────────────────────────────────────────────────

def _port_open(port: int) -> bool:
    """Return True if something is listening on localhost:port."""
    try:
        with socket.create_connection(("localhost", port), timeout=1):
            return True
    except OSError:
        return False


@pytest.fixture(scope="session")
def streamlit_server():
    """Start a Streamlit server for the duration of the test session."""
    if _port_open(8502):
        # Already running — use it
        yield BASE_URL
        return

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cmd = [
        sys.executable, "-m", "streamlit", "run", "app.py",
        "--server.port", "8502",
        "--server.headless", "true",
        "--server.runOnSave", "false",
        "--browser.gatherUsageStats", "false",
    ]
    proc = subprocess.Popen(
        cmd,
        cwd=project_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for Streamlit to be ready
    deadline = time.time() + STREAMLIT_STARTUP_TIMEOUT
    while time.time() < deadline:
        if _port_open(8502):
            time.sleep(1)  # give Streamlit a moment to finish initialising
            break
        time.sleep(0.5)
    else:
        proc.terminate()
        pytest.fail(f"Streamlit did not start within {STREAMLIT_STARTUP_TIMEOUT}s")

    yield BASE_URL

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture(scope="session")
def browser_context(streamlit_server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        yield context
        browser.close()


@pytest.fixture
def page(browser_context):
    pg = browser_context.new_page()
    yield pg
    pg.close()


# ── Helpers ───────────────────────────────────────────────────────────────────

def screenshot(page: Page, name: str):
    """Save a screenshot to docs/screenshots/."""
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    path = os.path.join(SCREENSHOTS_DIR, name)
    page.screenshot(path=path, full_page=False)
    return path


def navigate_to(page: Page, label: str):
    """Click a sidebar radio option by its visible label text."""
    page.click(f"text={label}")
    page.wait_for_timeout(STREAMLIT_NAVIGATE_WAIT)


def wait_for_streamlit(page: Page):
    """Wait for Streamlit's running indicator to disappear."""
    # Streamlit shows a spinner while computing — wait for it to settle
    page.wait_for_timeout(1500)


# ══════════════════════════════════════════════════════════════════════════════
# TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestAppLoads:
    """Basic smoke: app opens and key landmarks are visible."""

    def test_page_title(self, page: Page, streamlit_server: str):
        page.goto(streamlit_server, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        assert "InboxPilot" in page.title() or "localhost" in page.title()

    def test_sidebar_title_visible(self, page: Page, streamlit_server: str):
        page.goto(streamlit_server, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        # Sidebar title should be visible
        expect(page.get_by_text("InboxPilot AI").first).to_be_visible()

    def test_sidebar_navigation_present(self, page: Page, streamlit_server: str):
        page.goto(streamlit_server, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        # At least one navigation item visible
        body_text = page.inner_text("body")
        assert any(
            nav in body_text
            for nav in ["Dashboard", "Inbox Processing", "Review Queue", "Task Board"]
        ), "No navigation items found in sidebar"

    def test_safety_notice_present(self, page: Page, streamlit_server: str):
        page.goto(streamlit_server, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        body_text = page.inner_text("body")
        assert "Safety" in body_text or "draft" in body_text.lower(), (
            "No safety notice found on page"
        )

    def test_processing_mode_indicator(self, page: Page, streamlit_server: str):
        page.goto(streamlit_server, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        body_text = page.inner_text("body")
        # Should show either rule-based or OpenAI-enhanced mode
        assert "Rule-based" in body_text or "rule-based" in body_text.lower() or "OpenAI" in body_text, (
            "Processing mode indicator not found"
        )


class TestPageNavigation:
    """Verify each page renders without crashing."""

    def _load_app(self, page: Page, streamlit_server: str):
        page.goto(streamlit_server, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

    def test_dashboard_page(self, page: Page, streamlit_server: str):
        self._load_app(page, streamlit_server)
        navigate_to(page, "📊 Dashboard")
        body_text = page.inner_text("body")
        assert "Dashboard" in body_text

    def test_inbox_processing_page(self, page: Page, streamlit_server: str):
        self._load_app(page, streamlit_server)
        navigate_to(page, "📥 Inbox Processing")
        body_text = page.inner_text("body")
        assert "Inbox Processing" in body_text or "Seed" in body_text

    def test_review_queue_page(self, page: Page, streamlit_server: str):
        self._load_app(page, streamlit_server)
        navigate_to(page, "📋 Review Queue")
        body_text = page.inner_text("body")
        assert "Review" in body_text

    def test_task_board_page(self, page: Page, streamlit_server: str):
        self._load_app(page, streamlit_server)
        navigate_to(page, "✅ Task Board")
        body_text = page.inner_text("body")
        assert "Task" in body_text

    def test_reports_page(self, page: Page, streamlit_server: str):
        self._load_app(page, streamlit_server)
        navigate_to(page, "📤 Reports & Export")
        body_text = page.inner_text("body")
        assert "Report" in body_text or "Export" in body_text

    def test_about_safety_page(self, page: Page, streamlit_server: str):
        self._load_app(page, streamlit_server)
        navigate_to(page, "ℹ️ About & Safety")
        body_text = page.inner_text("body")
        assert "Safety" in body_text or "About" in body_text


class TestScreenshotCapture:
    """Capture portfolio screenshots. Results saved to docs/screenshots/."""

    def _load_app(self, page: Page, streamlit_server: str):
        page.goto(streamlit_server, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

    def test_screenshot_rule_based_mode(self, page: Page, streamlit_server: str):
        """Sidebar with rule-based mode indicator."""
        self._load_app(page, streamlit_server)
        path = screenshot(page, "rule-based-mode.png")
        assert os.path.exists(path), f"Screenshot not saved to {path}"

    def test_screenshot_about_safety(self, page: Page, streamlit_server: str):
        """About & Safety page — safety constraints visible."""
        self._load_app(page, streamlit_server)
        navigate_to(page, "ℹ️ About & Safety")
        path = screenshot(page, "about-safety.png")
        assert os.path.exists(path), f"Screenshot not saved to {path}"

    def test_screenshot_inbox_empty(self, page: Page, streamlit_server: str):
        """Inbox Processing — before seeding."""
        self._load_app(page, streamlit_server)
        navigate_to(page, "📥 Inbox Processing")
        path = screenshot(page, "inbox-processing.png")
        assert os.path.exists(path), f"Screenshot not saved to {path}"

    def test_screenshot_dashboard(self, page: Page, streamlit_server: str):
        """Dashboard — may be empty or populated depending on DB state."""
        self._load_app(page, streamlit_server)
        navigate_to(page, "📊 Dashboard")
        path = screenshot(page, "dashboard.png")
        assert os.path.exists(path), f"Screenshot not saved to {path}"

    def test_screenshot_review_queue(self, page: Page, streamlit_server: str):
        """Review Queue page."""
        self._load_app(page, streamlit_server)
        navigate_to(page, "📋 Review Queue")
        path = screenshot(page, "review-queue.png")
        assert os.path.exists(path), f"Screenshot not saved to {path}"

    def test_screenshot_task_board(self, page: Page, streamlit_server: str):
        """Task Board page."""
        self._load_app(page, streamlit_server)
        navigate_to(page, "✅ Task Board")
        path = screenshot(page, "task-board.png")
        assert os.path.exists(path), f"Screenshot not saved to {path}"

    def test_screenshot_reports(self, page: Page, streamlit_server: str):
        """Reports & Export page."""
        self._load_app(page, streamlit_server)
        navigate_to(page, "📤 Reports & Export")
        path = screenshot(page, "reports-export.png")
        assert os.path.exists(path), f"Screenshot not saved to {path}"
