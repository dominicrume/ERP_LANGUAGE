"""PRODUCT.md #5: instructors get a real authoring surface, not a config
file exposed as a UI. These tests hold the line on BREAK.md hat 2 — can an
instructor with no coding background author a valid scenario today?"""
import shutil
from pathlib import Path

import pytest
import yaml

from erpsim import authoring, templates, locales


@pytest.fixture
def sandbox_templates(tmp_path, monkeypatch):
    d = tmp_path / "templates"
    shutil.copytree(templates._DIR, d)
    monkeypatch.setattr(templates, "_DIR", d)
    return d


def draft(**over):
    d = {
        "title": "Supplier Price Shock",
        "industry": "retail grocery",
        "narrative": "Your main supplier of {{product}} has raised prices 30% overnight.",
        "product_pool": ["coffee beans", "cooking oil"],
        "decisions": [{
            "label": "Do you absorb the increase or pass it on?",
            "options": [
                {"label": "Absorb it", "points": -8, "reason": "Absorbing protects volume but costs margin: [points] pts."},
                {"label": "Pass it on", "points": -4, "multiply_by": "payment_terms_days",
                 "reason": "Passing it on in [country] bites harder with [payment terms]-day terms: [points] pts."},
            ],
        }],
        "kpi_weights": {"margin": 60, "customer satisfaction": 40},
    }
    d.update(over)
    return d


# ---------------------------------------------------------------- draft -> template
def test_draft_becomes_a_valid_template_with_ids_derived_from_words():
    tpl = authoring.from_draft(draft())
    templates.validate(tpl)  # the one validator, no second schema
    assert tpl["id"] == "supplier_price_shock"
    assert tpl["decisions"][0]["id"] == "do_you_absorb_the_increase_or_pass_it_on"  # slug, capped at 40
    assert tpl["decisions"][0]["options"] == ["absorb_it", "pass_it_on"]
    assert tpl["kpi_weights"] == {"margin": 0.6, "customer_satisfaction": 0.4}


def test_friendly_tokens_become_interpreter_fields():
    tpl = authoring.from_draft(draft())
    reason = tpl["decisions"][0]["scoring"]["pass_it_on"]["reason"]
    assert "{locale}" in reason and "{payment_terms_days}" in reason and "{delta}" in reason
    assert "[" not in reason


def test_instructor_never_sees_a_stack_trace_only_a_sentence():
    bad = draft(kpi_weights={"margin": 60, "satisfaction": 30})
    with pytest.raises(authoring.DraftError) as e:
        authoring.from_draft(bad)
    assert str(e.value) == "KPI weights must add up to 100%, they add up to 90%"


@pytest.mark.parametrize("over,fragment", [
    ({"title": ""}, "A title is missing"),
    ({"narrative": "No product mentioned here."}, "Insert product"),
    ({"product_pool": []}, "at least one product"),
    ({"decisions": []}, "at least one decision"),
    ({"decisions": [{"label": "Only one option?", "options": [{"label": "a", "points": 1, "reason": "r"}]}]},
     "at least two options"),
    ({"kpi_weights": {}}, "at least one KPI"),
])
def test_every_draft_mistake_has_a_plain_language_message(over, fragment):
    with pytest.raises(authoring.DraftError, match=fragment):
        authoring.from_draft(draft(**over))


def test_option_missing_its_reason_is_caught_in_the_instructors_words():
    d = draft()
    d["decisions"][0]["options"][0]["reason"] = "  "
    with pytest.raises(authoring.DraftError, match="write the reason learners will see"):
        authoring.from_draft(d)


def test_scale_with_must_be_a_real_locale_field():
    d = draft()
    d["decisions"][0]["options"][0]["multiply_by"] = "moon_phase"
    with pytest.raises(authoring.DraftError, match="can only scale with"):
        authoring.from_draft(d)


def test_duplicate_decision_names_are_refused():
    d = draft()
    d["decisions"] = [d["decisions"][0], dict(d["decisions"][0])]
    with pytest.raises(authoring.DraftError, match="already used"):
        authoring.from_draft(d)


# ---------------------------------------------------------------- round trip
def test_published_templates_open_back_in_the_builder():
    """An instructor can edit what shipped, not just create new."""
    for tid in templates.available():
        d = authoring.to_draft(templates.load(tid))
        assert authoring.from_draft(d)["id"] == tid


def test_round_trip_preserves_scoring_exactly():
    from erpsim import generator, scoring
    for tid in templates.available():
        original = templates.load(tid)
        rebuilt = authoring.from_draft(authoring.to_draft(original))
        for lid in locales.available():
            a = generator.generate_from(original, locales.load(lid), 1)
            b = generator.generate_from(rebuilt, locales.load(lid), 1)
            for d in a["decisions"]:
                for opt in d["options"]:
                    assert scoring.score_decision(a, d["id"], opt)["score_delta"] == \
                           scoring.score_decision(b, d["id"], opt)["score_delta"], (tid, lid, opt)


# ---------------------------------------------------------------- preview
def test_preview_shows_the_scenario_in_every_country():
    p = authoring.preview(authoring.from_draft(draft()))
    assert [l["locale_id"] for l in p["locales"]] == locales.available()
    for l in p["locales"]:
        assert "{{product}}" not in l["narrative"]
        assert l["decisions"][0]["options"][0]["justification"]


def test_preview_proves_the_authored_scenario_is_genuinely_localized():
    """The instructor sees the thesis applied to their OWN scenario: an
    option that scales with a locale field scores differently per country."""
    p = authoring.preview(authoring.from_draft(draft()))
    deltas = {l["locale_id"]: l["decisions"][0]["options"][1]["score_delta"] for l in p["locales"]}
    assert len(set(deltas.values())) == len(locales.available()), deltas


def test_preview_never_touches_the_config_directory(sandbox_templates):
    before = sorted(p.name for p in sandbox_templates.glob("*.yaml"))
    authoring.preview(authoring.from_draft(draft()))
    assert sorted(p.name for p in sandbox_templates.glob("*.yaml")) == before


# ---------------------------------------------------------------- publish
def test_publishing_writes_one_yaml_file_and_grows_the_catalog(sandbox_templates):
    before = len(templates.available())
    tpl = authoring.from_draft(draft())
    result = authoring.publish(tpl)
    assert result["published"] == "supplier_price_shock" and result["overwrote"] is False
    assert len(templates.available()) == before + 1
    written = yaml.safe_load((sandbox_templates / "supplier_price_shock.yaml").read_text())
    assert written == tpl  # the file IS the template, no lossy conversion


def test_published_file_is_readable_by_a_human(sandbox_templates):
    authoring.publish(authoring.from_draft(draft()))
    text = (sandbox_templates / "supplier_price_shock.yaml").read_text()
    assert text.startswith("# Authored in the instructor builder")
    assert "Supplier Price Shock" in text


def test_publishing_over_an_existing_id_is_refused_by_default(sandbox_templates):
    authoring.publish(authoring.from_draft(draft()))
    with pytest.raises(FileExistsError):
        authoring.publish(authoring.from_draft(draft()))


def test_overwrite_archives_the_previous_version(sandbox_templates):
    authoring.publish(authoring.from_draft(draft()))
    result = authoring.publish(authoring.from_draft(draft(title="Supplier Price Shock",
                                                          industry="wholesale")), overwrite=True)
    assert result["overwrote"] is True
    archived = Path(result["archived"])
    assert archived.exists() and yaml.safe_load(archived.read_text())["industry"] == "retail grocery"
    assert templates.load("supplier_price_shock")["industry"] == "wholesale"


def test_archive_folder_is_not_mistaken_for_a_template(sandbox_templates):
    authoring.publish(authoring.from_draft(draft()))
    authoring.publish(authoring.from_draft(draft()), overwrite=True)
    assert all("/" not in t and "." not in t for t in templates.available())


def test_a_published_scenario_is_immediately_playable_in_every_locale(sandbox_templates):
    from erpsim import generator
    authoring.publish(authoring.from_draft(draft()))
    for lid in locales.available():
        s = generator.generate("supplier_price_shock", lid, seed=3)
        assert s["title"] == "Supplier Price Shock" and "{{product}}" not in s["narrative"]


def test_publishing_requires_no_src_changes(sandbox_templates):
    """ENGINEERING.md #2 still holds: the builder writes config, not code."""
    authoring.publish(authoring.from_draft(draft()))
    for py in (Path(__file__).resolve().parents[1] / "src" / "erpsim").glob("*.py"):
        assert "supplier_price_shock" not in py.read_text()
