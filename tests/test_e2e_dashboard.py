import pytest
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = ROOT / "iterations" / "1-20260424_020912" / "artifacts"
SCREENSHOT_PATH = ARTIFACT_DIR / "dashboard.png"


def test_dashboard_renders_and_screenshot_saved(live_server):
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    base = live_server["base"]
    tid = live_server["trainer_id"]
    mid = live_server["member_ids"][0]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 900})

            page.goto(f"{base}/login")
            page.fill('input[name="username"]', live_server["username"])
            page.fill('input[name="password"]', live_server["password"])
            page.click('form[action="/login"] button[type="submit"]')
            page.wait_for_load_state("networkidle")

            page.goto(f"{base}/trainers/{tid}/members/{mid}/dashboard")

            page.wait_for_selector("canvas#max-weight-chart", timeout=10_000)
            page.wait_for_selector("canvas#total-volume-chart", timeout=10_000)

            page.wait_for_function(
                """() => {
                    if (typeof Chart === 'undefined') return false;
                    const a = Chart.getChart('max-weight-chart');
                    const b = Chart.getChart('total-volume-chart');
                    return a && b
                      && a.data.labels && a.data.labels.length > 0
                      && b.data.labels && b.data.labels.length > 0;
                }""",
                timeout=10_000,
            )

            page.screenshot(path=str(SCREENSHOT_PATH), full_page=True)
        finally:
            browser.close()

    assert SCREENSHOT_PATH.exists(), f"screenshot not saved: {SCREENSHOT_PATH}"
    assert SCREENSHOT_PATH.stat().st_size > 10_000, "screenshot suspiciously small"
