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


# ---- KPI impacts in the builder (PROMPT-02 item 5) ----

def impact_draft(**over):
    d = draft()
    d["decisions"][0]["options"] = [
        {"label": "Absorb it", "reason": "Absorbing costs margin: [points] pts.",
         "impacts": [{"kpi": "margin", "points": -20},
                     {"kpi": "customer satisfaction", "points": 8}]},
        {"label": "Pass it on", "reason": "Passing it on in [country]: [points] pts.",
         "impacts": [{"kpi": "customer satisfaction", "points": -12,
                      "scales_with": "freight_expedite_multiplier"}]},
    ]
    d.update(over)
    return d


def test_a_draft_can_author_impacts_per_kpi():
    tpl = authoring.from_draft(impact_draft())
    templates.validate(tpl)
    rule = tpl["decisions"][0]["scoring"]["absorb_it"]
    assert rule["impact"] == {"margin": {"points": -20}, "customer_satisfaction": {"points": 8}}
    assert "points" not in rule
    other = tpl["decisions"][0]["scoring"]["pass_it_on"]["impact"]["customer_satisfaction"]
    assert other["scales_with"] == "freight_expedite_multiplier"


def test_an_impact_on_a_kpi_the_scenario_does_not_measure_is_refused_in_plain_words():
    d = impact_draft()
    d["decisions"][0]["options"][0]["impacts"][0]["kpi"] = "reputation"
    with pytest.raises(authoring.DraftError, match="'reputation' is not one of the KPIs this scenario measures"):
        authoring.from_draft(d)


def test_the_same_kpi_twice_on_one_option_is_refused():
    d = impact_draft()
    d["decisions"][0]["options"][0]["impacts"].append({"kpi": "margin", "points": 5})
    with pytest.raises(authoring.DraftError, match="listed twice"):
        authoring.from_draft(d)


def test_an_option_that_says_nothing_about_any_kpi_is_refused():
    """A client that drops the scoring must be told, not silently published
    with every option worth nothing."""
    d = impact_draft()
    d["decisions"][0]["options"][0].pop("impacts")
    with pytest.raises(authoring.DraftError, match="say what this choice does"):
        authoring.from_draft(d)


def test_editing_a_weighted_template_cannot_flatten_it():
    """The regression this test exists for: a builder that knew only about
    `points` would reopen a weighted template and republish it scoring 0."""
    for tid in templates.available():
        d = authoring.to_draft(templates.load(tid))
        for dec in d["decisions"]:
            for opt in dec["options"]:
                assert opt["impacts"], f"{tid}.{dec['id']}.{opt['id']} lost its impacts"
                opt.pop("impacts")
        with pytest.raises(authoring.DraftError):
            authoring.from_draft(d)


def test_a_legacy_template_opens_as_impacts_so_editing_converts_it():
    legacy = yaml.safe_load((Path(__file__).parent / "fixtures" / "heatwave_v0.2_legacy.yaml").read_text())
    d = authoring.to_draft(legacy)
    expedite = [o for o in d["decisions"][1]["options"] if o["id"] == "expedite"][0]
    assert expedite["legacy_points"] == -20
    assert expedite["impacts"] == [{"kpi": "cash position", "points": -20,
                                    "scales_with": "freight_expedite_multiplier"}]
    converted = authoring.from_draft(d)
    assert "impact" in converted["decisions"][1]["scoring"]["expedite"]


def test_preview_shows_the_best_and_worst_a_learner_could_finish_on():
    """PRODUCT.md #6 applied to authoring: the instructor sees the real
    range of their own scenario in each country, not one decision at a time."""
    p = authoring.preview(authoring.from_draft(impact_draft()))
    for loc in p["locales"]:
        best, worst = loc["best_run"], loc["worst_run"]
        assert 0.0 <= worst["final_score"] <= best["final_score"] <= 100.0
        assert len(best["choices"]) == len(worst["choices"]) == 1
        assert best["choices"][0]["score_delta"] >= worst["choices"][0]["score_delta"]


def test_the_previewed_range_differs_by_country_when_a_rule_scales():
    """The range a learner can finish on, not one decision. Two countries may
    share a best or a worst score, because the best path can be the same
    option in both; the pair of them is what must differ."""
    p = authoring.preview(authoring.from_draft(impact_draft()))
    ranges = {l["locale_id"]: (l["best_run"]["final_score"], l["worst_run"]["final_score"])
              for l in p["locales"]}
    assert len(set(ranges.values())) == len(ranges), ranges


def test_a_wildly_negative_option_still_reports_a_score_of_zero_not_a_negative():
    """An instructor can author numbers that would take a learner below
    zero. The preview must show the floor, not a nonsense negative."""
    d = impact_draft()
    d["decisions"][0]["options"][1]["impacts"] = [
        {"kpi": "margin", "points": -500, "scales_with": "payment_terms_days"}]
    p = authoring.preview(authoring.from_draft(d))
    assert all(l["worst_run"]["final_score"] == 0.0 for l in p["locales"])


def test_preview_carries_the_kpi_breakdown_for_every_option():
    p = authoring.preview(authoring.from_draft(impact_draft()))
    rows = p["locales"][0]["decisions"][0]["options"][0]["kpi_breakdown"]
    assert {r["kpi"] for r in rows} == {"margin", "customer_satisfaction"}
    assert all("weighted" in r for r in rows)
