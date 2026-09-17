"""The learner's sitting, played in a real browser, start to finish.

This is the file that would have caught the defect the product shipped
with: a learner could turn over every card and the screen simply stopped,
while the score on it discarded every earlier decision.
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

PORT = 8129


@pytest.fixture(scope="module")
def browser_and_url():
    box = Path(tempfile.mkdtemp(prefix="erpsim-learner-"))
    for sub in ("config", "src", "static"):
        shutil.copytree(ROOT / sub, box / sub)
    srv = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "erpsim.main:app", "--app-dir", "src",
         "--port", str(PORT), "--log-level", "warning"],
        cwd=box, env={**os.environ, "ERPSIM_DATABASE_URL": f"sqlite:///{box}/learner.db"},
        stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    for _ in range(80):
        try:
            socket.create_connection(("127.0.0.1", PORT), 0.3).close()
            break
        except OSError:
            time.sleep(0.25)
    else:
        srv.terminate(); shutil.rmtree(box, ignore_errors=True); pytest.fail("server did not start")
    try:
        with sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except PWError as e:
                pytest.skip(f"chromium not installed: {e}")
            yield browser, f"http://127.0.0.1:{PORT}/"
            browser.close()
    finally:
        srv.terminate(); srv.wait(); shutil.rmtree(box, ignore_errors=True)


def _page(browser, url, **ctx):
    ctx.setdefault("viewport", {"width": 1280, "height": 900})
    context = browser.new_context(**ctx)
    page = context.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(url, wait_until="networkidle")
    return context, page


def _begin(page, learner="amina", template="heatwave_demand", locale="nigeria"):
    page.fill("#learnerId", learner)
    page.select_option("#templateSelect", template)
    page.select_option("#localeSelect", locale)
    page.click("#beginBtn")
    page.wait_for_selector(".scenario.show .opt")


def _answer_every_card(page):
    """Turn over each card in turn, collecting what the learner is shown."""
    seen = []
    total = page.locator(".decision").count()
    for i in range(total):
        page.locator(f"#cardInner-{i} .opt").first.click()
        page.wait_for_selector(f"#cardInner-{i}.flipped")
        page.wait_for_timeout(250)
        delta = page.locator(f"#cardBack-{i} .delta").inner_text()
        seen.append((float(delta.replace("points", "").strip()),
                     float(page.locator("#statRunning").inner_text())))
    return seen


def test_a_learner_can_finish_a_scenario_and_is_told_how_they_did(browser_and_url):
    browser, url = browser_and_url
    ctx, page = _page(browser, url)
    _begin(page)
    assert "Decision 1 of 2" in page.locator("#runProgress").inner_text()

    _answer_every_card(page)
    page.wait_for_selector(".finish.show", timeout=8000)

    finish = page.locator("#finishCard").inner_text()
    assert "That is the whole scenario" in finish
    final = float(page.locator("#finalScore").inner_text())
    assert 0.0 <= final <= 100.0
    assert "out of 100" in finish
    # every decision is accounted for, with the reason that produced it
    assert page.locator(".finish-row").count() == 2
    assert "What cost you most" in finish
    assert "day streak" in finish
    assert not page.errors, page.errors
    ctx.close()


def test_the_score_on_screen_adds_the_decisions_up(browser_and_url):
    """CONTEXT.md gap A, as a learner would meet it: the number after the
    second card must include the first."""
    browser, url = browser_and_url
    ctx, page = _page(browser, url)
    _begin(page, learner="bo")
    seen = _answer_every_card(page)
    # The server keeps the raw total and clamps for display, so a decision
    # that takes the run above 100 is not quietly banked at 100.
    raw = 100.0
    for delta, shown in seen:
        raw = round(raw + delta, 1)
        assert shown == min(100.0, max(0.0, raw)), seen
    page.wait_for_selector(".finish.show")
    assert float(page.locator("#finalScore").inner_text()) == seen[-1][1]
    ctx.close()


def test_the_record_counts_finished_sittings_and_shows_a_streak(browser_and_url):
    browser, url = browser_and_url
    ctx, page = _page(browser, url)
    _begin(page, learner="cleo")
    _answer_every_card(page)
    page.wait_for_selector(".finish.show")
    assert page.locator("#scorebar").inner_text().count("1") >= 1

    page.click("#playAgainBtn")
    page.wait_for_selector(".scenario.show .opt")
    assert not page.locator(".finish").is_visible()
    _answer_every_card(page)
    page.wait_for_selector(".finish.show")
    assert "2" in page.locator("#finishStreak").inner_text()      # two sittings finished

    page.reload(wait_until="networkidle")
    # The page comes back to the same name, scenario and country.
    assert page.locator("#learnerId").input_value() == "cleo"
    assert page.locator("#localeSelect").input_value() == "nigeria"
    page.wait_for_selector("#memoryStrip.show", timeout=6000)
    strip = page.locator("#memoryText").inner_text()
    assert "finished this scenario" in strip and "out of 100" in strip
    ctx.close()


def test_losing_the_page_mid_sitting_does_not_lose_the_sitting(browser_and_url):
    """BREAK.md Firefighter: the run lives on the server, so a reload picks
    up where the learner left off instead of starting again."""
    browser, url = browser_and_url
    ctx, page = _page(browser, url)
    _begin(page, learner="dara")
    page.locator("#cardInner-0 .opt").first.click()
    page.wait_for_selector("#cardInner-0.flipped")
    page.wait_for_timeout(300)
    before = page.locator("#statRunning").inner_text()

    page.reload(wait_until="networkidle")
    page.wait_for_selector("#cardInner-0.flipped", timeout=8000)
    assert page.locator("#statRunning").inner_text() == before
    assert "Decision 2 of 2" in page.locator("#runProgress").inner_text()
    assert page.locator("#learnerId").input_value() == "dara"

    page.locator("#cardInner-1 .opt").first.click()
    page.wait_for_selector(".finish.show", timeout=8000)
    assert page.locator(".finish-row").count() == 2
    ctx.close()


def test_a_card_cannot_be_answered_twice_from_the_keyboard(browser_and_url):
    browser, url = browser_and_url
    ctx, page = _page(browser, url)
    _begin(page, learner="eli")
    page.locator("#cardInner-0 .opt").first.click()
    page.wait_for_selector("#cardInner-0.flipped")
    page.wait_for_timeout(300)
    assert page.evaluate("document.querySelector('#cardInner-0 .card-front').inert") is True
    assert page.evaluate("document.activeElement.classList.contains('card-back')")
    ctx.close()


def test_the_finished_card_survives_dark_mode_and_a_phone(browser_and_url):
    browser, url = browser_and_url
    ctx, page = _page(browser, url, color_scheme="dark", viewport={"width": 375, "height": 812})
    _begin(page, learner="fay")
    _answer_every_card(page)
    page.wait_for_selector(".finish.show")
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
    assert page.evaluate("""() => {
        const el = document.getElementById('finalScore'); const r = el.getBoundingClientRect();
        return r.width > 0 && r.left >= 0 && r.right <= window.innerWidth + 1 }""")
    assert not page.errors, page.errors
    ctx.close()
