"""The frontend is a static file; these are the contract checks we can run
without a browser. ENGINEERING.md #6: one brain, one place."""
import re
from pathlib import Path

HTML = (Path(__file__).resolve().parents[1] / "static" / "index.html").read_text()


def test_no_alert_dialogs():
    """BREAK.md #4: failures are an honest inline state, not a modal."""
    assert "alert(" not in HTML


def test_running_score_comes_from_the_api_response():
    assert "result.running_score" in HTML
    assert "statRunning" in HTML


def test_frontend_never_reimplements_scoring_or_localization():
    """ENGINEERING.md #6: one brain, one place. The builder may carry the
    instructor's authored points to the API, but no score may be COMPUTED
    here — points are never combined with a locale rule client-side.
    (Rendering a rate as a percentage, tax_rate*100, is display, not logic.)"""
    script = HTML.split("<script>")[1]
    arithmetic = re.sub(r"tax_rate\s*\*\s*100", "", script)
    assert not re.search(r"\b(tax_rate|freight_expedite_multiplier|payment_terms_days|score_delta|running_score)\s*[*+\-/]",
                         arithmetic)
    # points never multiplied by anything, and never combined with a locale rule
    assert not re.search(r"\bpoints\b\s*[*/]", arithmetic)
    assert not re.search(r"[*/]\s*\w*\.?\bpoints\b", arithmetic)
    for rule in ("freight_expedite_multiplier", "payment_terms_days", "tax_rate"):
        assert not re.search(rf"points[^;\n]*{rule}|{rule}[^;\n]*points", arithmetic)


def test_frontend_scores_with_locale_id():
    assert "locale: currentScenario.locale_id" in HTML


def test_learner_data_promise_is_stated_in_product():
    """PRODUCT.md #7: in-product, not in terms."""
    assert 'id="identityNote"' in HTML and "never shown to another learner" in HTML


# ---- UI quality contract (redesign 2026-09-17: taste-skill + ui-ux-pro-max audit) ----

VISIBLE = re.sub(r"<style>.*?</style>", "", HTML, flags=re.S)
STYLE = HTML.split("<style>")[1].split("</style>")[0]


def test_no_em_or_en_dashes_anywhere_a_user_can_read():
    assert not re.search("[—–]|&mdash;|&ndash;", VISIBLE)


def test_page_has_landmarks_skip_link_and_real_labels():
    assert "<main" in HTML and "<header" in HTML and "<nav" in HTML
    assert 'class="skip" href="#main"' in HTML
    for field in ("learnerId", "templateSelect", "localeSelect", "fTitle", "fIndustry", "fNarrative", "fProduct"):
        assert f'for="{field}"' in HTML, field


def test_dark_mode_and_reduced_motion_are_supported():
    assert "@media (prefers-color-scheme: dark)" in STYLE
    assert "@media (prefers-reduced-motion:reduce)" in STYLE
    assert ":focus-visible" in STYLE


def test_colors_come_from_tokens_only():
    """One palette, defined once per theme. Raw hex outside the token blocks is
    how a second accent sneaks in."""
    token_blocks = re.findall(r":root\{.*?\n\}", STYLE, flags=re.S)
    outside = STYLE
    for block in token_blocks:
        outside = outside.replace(block, "")
    assert not re.findall(r"#[0-9A-Fa-f]{3,8}\b", outside)


def test_authored_strings_never_reach_an_inline_handler_in_the_learner_view():
    """Decision and option ids travel in data attributes read by a delegated
    listener, never interpolated into onclick JavaScript."""
    assert "onclick=\"makeDecision(" not in HTML
    assert "data-decision=" in HTML and "data-choice=" in HTML


def test_score_labels_do_not_claim_what_the_api_does_not_compute():
    """CONTEXT.md gap A: the API scores each decision on its own. Until runs
    exist (PROMPT-02 item 1) the UI must not call it a running score."""
    assert "Running score" not in VISIBLE and "Attempts<" not in VISIBLE
