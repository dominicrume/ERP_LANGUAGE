"""Exit criterion (PROMPT-01 §5, ENGINEERING.md Rule 2): a fifth country and a
third industry are two new YAML files. They generate and score through the
API with zero edits to src/. The files live in tmp_path; src/ is grepped
to prove it knows nothing about them."""
import shutil
from pathlib import Path

import pytest
from erpsim import locales, templates

ROOT = Path(__file__).resolve().parents[1]

KENYA = """\
code: KE
currency: KES
tax:
  type: VAT
  standard_rate: 0.16
  reduced_rate: 0.08
  notes: "VAT at 16%; withholding VAT of 2% applies to appointed agents."
freight_expedite_multiplier: 2.4
payment_terms_days: 60
accounting_period: "calendar_month"
"""

COLD_SNAP = """\
id: cold_snap
industry: retail_grocery
title: "Cold Snap Stockout"
narrative: "A cold snap has emptied shelves of {{product}}. Decide how to restock."
product_pool: ["soup", "heaters"]
decisions:
  - id: restock
    label: "How do you restock?"
    options: ["air_freight", "wait_for_truck"]
    scoring:
      air_freight:
        points: -15
        multiply_by: freight_expedite_multiplier
        reason: "Air freight in {locale} runs at {freight_expedite_multiplier}x: {points:.1f} pts."
      wait_for_truck:
        points: -3
        multiply_by: payment_terms_days
        reason: "Waiting ties up cash for {payment_terms_days} days of terms: {points:.1f} pts."
kpi_weights: { cash_position: 0.5, customer_satisfaction: 0.5 }
"""


@pytest.fixture
def grown_config(tmp_path, monkeypatch):
    ldir = tmp_path / "locales"; shutil.copytree(locales._DIR, ldir)
    tdir = tmp_path / "templates"; shutil.copytree(templates._DIR, tdir)
    (ldir / "kenya.yaml").write_text(KENYA)
    (tdir / "cold_snap.yaml").write_text(COLD_SNAP)
    monkeypatch.setattr(locales, "_DIR", ldir)
    monkeypatch.setattr(templates, "_DIR", tdir)


def test_src_knows_nothing_about_the_new_files():
    for py in (ROOT / "src" / "erpsim").glob("*.py"):
        text = py.read_text().lower()
        assert "kenya" not in text and "cold_snap" not in text, py.name


def test_fifth_locale_and_third_template_grow_the_catalog_with_zero_src_changes(client, grown_config):
    cat = client.get("/catalog").json()
    assert "kenya" in cat["locales"] and "cold_snap" in cat["templates"]
    assert cat["possible_scenarios"] == 15  # 3 x 5

    # New template x new locale, generated and scored through the API.
    s = client.post("/scenarios/generate", data=dict(template_id="cold_snap", locale="kenya", seed=7)).json()
    assert s["currency"] == "KES" and s["locale_rules"]["tax_rate"] == 0.16
    for choice in ("air_freight", "wait_for_truck"):
        r = client.post("/decisions/score", data=dict(template_id="cold_snap", locale="kenya", seed=7,
                                                       decision_id="restock", choice=choice, learner_id="amina"))
        assert r.status_code == 200, r.text
    air = client.post("/decisions/score", data=dict(template_id="cold_snap", locale="kenya", seed=7,
                                                     decision_id="restock", choice="air_freight")).json()
    assert air["score_delta"] == -36.0  # -15 x 2.4, from the two YAML files alone
    assert "2.4x" in air["justification"][0]

    # New template x old locale, and old template x new locale, also work.
    assert client.post("/scenarios/generate", data=dict(template_id="cold_snap", locale="uk", seed=1)).status_code == 200
    assert client.post("/scenarios/generate", data=dict(template_id="heatwave_demand", locale="kenya", seed=1)).status_code == 200

    # And the learner's memory for the new pair is real.
    p = client.get("/learners/amina/progress/cold_snap", params={"locale": "kenya"}).json()
    assert p["attempts"] == 2 and p["last_mistake"]
