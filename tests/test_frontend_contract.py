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
    # No tax rates, multipliers or point values are computed client-side.
    # (Rendering a rate as a percentage, tax_rate*100, is display, not logic.)
    script = HTML.split("<script>")[1]
    arithmetic = re.sub(r"tax_rate\s*\*\s*100", "", script)
    assert not re.search(r"\b(tax_rate|freight_expedite_multiplier|score_delta|running_score)\s*[*+\-/]", arithmetic)
    assert "points" not in re.sub(r"<textarea.*?</textarea>", "", HTML, flags=re.S).split("<script>")[1]


def test_frontend_scores_with_locale_id():
    assert "locale: currentScenario.locale_id" in HTML


def test_learner_data_promise_is_stated_in_product():
    """PRODUCT.md #7: in-product, not in terms."""
    assert 'id="identityNote"' in HTML and "never shown to another learner" in HTML
