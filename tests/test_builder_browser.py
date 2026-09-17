"""BREAK.md hat 2, answered in a real browser: can an instructor with no
coding background author a valid scenario through the UI alone, today?

Skipped unless Playwright and a Chromium build are present:
    pip install -e ".[ui]" && playwright install chromium
It is skipped, never silently passed — a skip here means the claim is
unverified on this machine, not that it holds.
"""
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
pytest.importorskip("playwright.sync_api", reason="playwright not installed")
from playwright.sync_api import Error as PWError, sync_playwright  # noqa: E402

PORT = 8124


@pytest.fixture(scope="module")
def instructor_page():
    """A server on a copy of the repo, so publishing never writes to config/."""
    sandbox = Path(tempfile.mkdtemp(prefix="erpsim-ui-"))
    for sub in ("config", "src", "static"):
        shutil.copytree(ROOT / sub, sandbox / sub)
    env = {**os.environ, "ERPSIM_DATABASE_URL": f"sqlite:///{sandbox}/ui.db"}
    srv = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "erpsim.main:app", "--app-dir", "src",
         "--port", str(PORT), "--log-level", "warning"],
        cwd=sandbox, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    for _ in range(80):
        try:
            socket.create_connection(("127.0.0.1", PORT), 0.3).close()
            break
        except OSError:
            time.sleep(0.25)
    else:
        srv.terminate()
        shutil.rmtree(sandbox, ignore_errors=True)
        pytest.fail("server did not start")

    try:
        with sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except PWError as e:
                pytest.skip(f"chromium not installed: {e}")
            page = browser.new_page(viewport={"width": 1280, "height": 1000})
            page.errors = []
            page.on("pageerror", lambda e: page.errors.append(str(e)))
            page.goto(f"http://127.0.0.1:{PORT}/", wait_until="networkidle")
            yield page, sandbox
            browser.close()
    finally:
        srv.terminate(); srv.wait()
        shutil.rmtree(sandbox, ignore_errors=True)


def _author_and_publish(page):
    page.click("#tabInstructor")
    page.wait_for_selector(".shelf-card", timeout=8000)
    page.click(".shelf-new")
    page.wait_for_selector("#builderPane", state="visible")
    page.fill("#fTitle", "Port Strike Delay")
    page.fill("#fIndustry", "manufacturing distribution")
    page.fill("#fNarrative", "A port strike has stranded your inbound {{product}} for two weeks.")
    page.fill("#fProduct", "steel coil")
    page.click("button.btn-sm:has-text('Add')")
    page.fill(".sub-card input[type=text]", "How do you cover the gap?")
    # Name what the scenario measures first: an option's impact points at it.
    rows = page.locator(".kpi-row")
    rows.nth(0).locator("input[type=text]").fill("cash position")
    rows.nth(0).locator("input[type=number]").fill("100")
    opts = page.locator(".opt-card")
    opts.nth(0).locator("input[type=text]").first.fill("Air freight a partial load")
    opts.nth(0).locator("select[id^=ok-]").select_option("cash position")
    opts.nth(0).locator("input[id^=op-]").fill("-12")
    opts.nth(0).locator("select[id^=os-]").select_option("freight_expedite_multiplier")
    opts.nth(0).locator("input[id^=reason]").fill(
        "Air freight in [country] runs at [expedite multiplier]x: [points] pts.")
    opts.nth(1).locator("input[type=text]").first.fill("Ration existing stock")
    opts.nth(1).locator("select[id^=ok-]").select_option("cash position")
    opts.nth(1).locator("input[id^=op-]").fill("-5")
    opts.nth(1).locator("input[id^=reason]").fill("Rationing holds cash but disappoints customers: [points] pts.")
    page.wait_for_selector(".pv-narrative", timeout=8000)


def test_an_instructor_can_author_and_publish_without_touching_yaml(instructor_page):
    page, sandbox = instructor_page
    _author_and_publish(page)

    # The instructor never sees the file format on the way in.
    form = page.locator("#builderPane").inner_text()
    for jargon in ("kpi_weights", "multiply_by", "scoring:", "scales_with", "impact:"):
        assert jargon not in form, jargon

    # Publish, and the file appears — one industry, one config file.
    page.click("#publishBtn")
    page.wait_for_selector(".banner.ok", timeout=8000)
    assert "Published" in page.locator("#builderBanner").inner_text()
    assert (sandbox / "config/templates/port_strike_delay.yaml").exists()
    assert not page.errors, page.errors


def test_preview_proves_localization_to_the_instructor(instructor_page):
    """The thesis, shown to the author about their OWN scenario."""
    page, _ = instructor_page
    assert page.locator(".loc-tab").count() == 4
    assert page.locator(".range").count() == 1        # the range a learner can finish on
    assert "Genuinely localized" in page.locator(".thesis").inner_text()
    deltas = []
    for i in range(4):
        page.locator(".loc-tab").nth(i).click()
        page.wait_for_timeout(300)
        deltas.append(page.locator(".pv-opt .d").first.inner_text())
    assert len(set(deltas)) == 4, deltas


def test_an_open_draft_survives_a_trip_to_the_learner_view(instructor_page):
    """Deliberate: peeking at the learner view must not discard the draft."""
    page, _ = instructor_page
    page.click("#tabLearner")
    page.click("#tabInstructor")
    assert page.locator("#builderPane").is_visible()
    assert page.input_value("#fTitle") == "Port Strike Delay"


def test_authored_scenario_is_immediately_playable_by_a_learner(instructor_page):
    page, _ = instructor_page
    page.click("button.btn-sm:has-text('Back to your scenarios')")
    page.wait_for_selector("#shelfPane", state="visible")
    page.click("#tabLearner")
    page.select_option("#templateSelect", "port_strike_delay")
    page.select_option("#localeSelect", "brazil")
    page.click("button:has-text('Begin scenario')")
    page.wait_for_selector(".scenario.show .opt", timeout=8000)
    page.locator(".opt").first.click()
    page.wait_for_selector(".card-inner.flipped", timeout=8000)
    assert "1.9x" in page.locator(".card-back").first.inner_text()
    shown = float(page.locator("#statRunning").inner_text())
    assert 0.0 <= shown < 100.0, shown      # an expedite choice always costs something


def test_a_published_scenario_reopens_in_the_builder_in_plain_language(instructor_page):
    page, _ = instructor_page
    page.click("#tabInstructor")
    page.wait_for_function("document.querySelectorAll('.shelf-card').length === 3", timeout=8000)
    page.locator(".shelf-card:has-text('Port Strike') button").click()
    page.wait_for_selector("#builderPane", state="visible")
    assert page.input_value("#fTitle") == "Port Strike Delay"
    reason = page.locator("input[id^=reason]").first.input_value()
    assert "[country]" in reason and "{" not in reason


def test_authored_text_can_never_run_as_script_in_a_learners_browser(instructor_page):
    """BREAK.md Thief hat. Publishing is open (DEBT.md), so every authored
    string reaching the learner view is untrusted. A decision label or option
    carrying markup must render as text and never execute."""
    page, _ = instructor_page
    payload = '<img src=x onerror="window.__xss=(window.__xss||0)+1">'
    draft = {
        "title": "Injection Probe", "industry": "security",
        "narrative": "A probe about {{product}}.", "product_pool": ["widgets"],
        "decisions": [{"label": "Pick one " + payload, "options": [
            {"label": "first", "points": 1, "reason": "Reason with " + payload + " [points]."},
            {"label": "second", "points": -1, "reason": "Other reason [points]."}]}],
        "kpi_weights": {"margin": 100},
    }
    r = page.request.post(f"http://127.0.0.1:{PORT}/instructor/drafts/publish", data=draft)
    assert r.ok, r.text()
    page.reload(wait_until="networkidle")
    page.click("#tabLearner")
    page.select_option("#templateSelect", "injection_probe")
    page.click("button:has-text('Begin scenario')")
    page.wait_for_selector(".scenario.show .opt", timeout=8000)
    page.locator(".opt").first.click()
    page.wait_for_selector(".card-inner.flipped", timeout=8000)
    page.wait_for_timeout(400)
    assert page.evaluate("window.__xss") is None, "authored markup executed as script"
    assert "<img" in page.locator(".decision-label").first.inner_text()
