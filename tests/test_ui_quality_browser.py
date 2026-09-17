"""UI quality, measured in a real browser in both themes and at phone width.

These lock in the 2026-09-17 redesign audit (taste-skill + ui-ux-pro-max):
contrast, no horizontal scroll, a one-line top bar, cards that never clip
their reason, keyboard focus that follows the reveal, and touch targets.
Skipped, never silently passed, without Playwright: pip install -e ".[ui]".
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

PORT = 8127

CONTRAST_FAILS = """() => {
  const lum = c => { const m = c.match(/[\\d.]+/g).map(Number).slice(0,3).map(v => { v/=255; return v<=.03928? v/12.92 : Math.pow((v+.055)/1.055, 2.4) });
                     return .2126*m[0] + .7152*m[1] + .0722*m[2] };
  const bgOf = el => { while(el){ const c = getComputedStyle(el).backgroundColor, a = (c.match(/[\\d.]+/g)||[]).map(Number);
                       if(a.length && (a.length<4 || a[3]>0.9)) return c; el = el.parentElement } return getComputedStyle(document.body).backgroundColor };
  const out = [];
  for(const el of document.querySelectorAll('body *')){
    if(!el.offsetParent) continue;
    if(![...el.childNodes].some(n => n.nodeType===3 && n.textContent.trim().length>1)) continue;
    if(el.closest('[aria-hidden="true"],[inert]')) continue;
    const s = getComputedStyle(el); if(s.visibility==='hidden' || +s.opacity===0) continue;
    const f = lum(s.color), b = lum(bgOf(el)), r = (Math.max(f,b)+.05)/(Math.min(f,b)+.05);
    const large = parseFloat(s.fontSize)>=24 || (parseFloat(s.fontSize)>=18.66 && +s.fontWeight>=700);
    if(r < (large?3:4.5)) out.push(`${el.className||el.tagName} "${el.textContent.trim().slice(0,30)}" ${r.toFixed(2)}`);
  }
  return out;
}"""


@pytest.fixture(scope="module")
def server():
    box = Path(tempfile.mkdtemp(prefix="erpsim-uiq-"))
    for sub in ("config", "src", "static"):
        shutil.copytree(ROOT / sub, box / sub)
    srv = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "erpsim.main:app", "--app-dir", "src", "--port", str(PORT), "--log-level", "warning"],
        cwd=box, env={**os.environ, "ERPSIM_DATABASE_URL": f"sqlite:///{box}/uiq.db"},
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
            yield browser
            browser.close()
    finally:
        srv.terminate(); srv.wait(); shutil.rmtree(box, ignore_errors=True)


def _play_first_card(page):
    page.goto(f"http://127.0.0.1:{PORT}/", wait_until="networkidle")
    page.select_option("#templateSelect", "heatwave_demand")
    page.select_option("#localeSelect", "nigeria")
    page.click("#beginBtn")
    page.wait_for_selector(".scenario.show .opt")
    page.locator(".opt").first.click()
    page.wait_for_selector(".card-inner.flipped")
    page.wait_for_timeout(650)


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("width", [1280, 375])
def test_learner_and_builder_pass_contrast_layout_and_focus(server, scheme, width):
    ctx = server.new_context(viewport={"width": width, "height": 900}, color_scheme=scheme)
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    _play_first_card(page)

    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "horizontal scroll"
    assert page.evaluate("document.querySelector('.topbar').getBoundingClientRect().height") <= 80, "top bar wrapped"
    assert page.evaluate("""[...document.querySelectorAll('.card-flip')].every(f =>
        [...f.querySelectorAll('.card-face')].every(face => face.getBoundingClientRect().height >= face.scrollHeight - 1))"""), \
        "a card face clips its content"
    # Keyboard and screen-reader users follow the reveal, and cannot re-answer a hidden card.
    assert page.evaluate("document.activeElement.classList.contains('card-back')")
    assert page.evaluate("[...document.querySelectorAll('.card-inner.flipped .card-front')].every(f => f.inert)")
    assert page.evaluate(CONTRAST_FAILS) == []

    page.click("#tabInstructor")
    page.wait_for_selector(".shelf-card")
    page.locator(".shelf-card button").first.click()
    page.wait_for_selector(".pv-narrative")
    page.wait_for_timeout(400)
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "builder scrolls sideways"
    assert page.evaluate(CONTRAST_FAILS) == []
    assert not errors, errors
    ctx.close()


def test_touch_devices_get_44px_targets_everywhere_that_matters(server):
    ctx = server.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
    page = ctx.new_page()
    page.goto(f"http://127.0.0.1:{PORT}/", wait_until="networkidle")
    small = page.evaluate("""[...document.querySelectorAll('.mode-toggle button, #learnerId, #templateSelect, #localeSelect, #beginBtn')]
        .map(e => [e.id || e.textContent.trim(), Math.round(e.getBoundingClientRect().height)]).filter(([, h]) => h < 44)""")
    assert small == [], small
    page.click("#tabInstructor")
    page.wait_for_selector(".shelf-card")
    page.locator(".shelf-card button").first.click()
    page.wait_for_selector(".pv-narrative")
    small = page.evaluate("""[...document.querySelectorAll('.btn-sm, .loc-tab, .btn')].filter(e => e.offsetParent)
        .map(e => [e.textContent.trim().slice(0, 20), Math.round(e.getBoundingClientRect().height)]).filter(([, h]) => h < 44)""")
    assert small == [], small
    ctx.close()


def test_skip_link_is_the_first_stop_and_lands_on_main(server):
    ctx = server.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    page.goto(f"http://127.0.0.1:{PORT}/", wait_until="networkidle")
    page.keyboard.press("Tab")
    assert page.evaluate("document.activeElement.className") == "skip"
    page.keyboard.press("Enter")
    assert page.evaluate("document.activeElement.id") == "main"
    ctx.close()
