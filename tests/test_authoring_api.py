"""The authoring surface over HTTP — what the builder UI actually calls."""
import shutil

import pytest

from erpsim import templates


@pytest.fixture
def sandbox_templates(tmp_path, monkeypatch):
    d = tmp_path / "templates"
    shutil.copytree(templates._DIR, d)
    monkeypatch.setattr(templates, "_DIR", d)
    return d


DRAFT = {
    "title": "Port Strike Delay",
    "industry": "manufacturing distribution",
    "narrative": "A port strike has stranded your inbound {{product}} for two weeks.",
    "product_pool": ["steel coil", "packaging film"],
    "decisions": [{
        "label": "How do you cover the gap?",
        "options": [
            {"label": "Air freight a partial load", "points": -12,
             "multiply_by": "freight_expedite_multiplier",
             "reason": "Air freight in [country] runs at [expedite multiplier]x: [points] pts."},
            {"label": "Ration existing stock", "points": -5,
             "reason": "Rationing holds cash but disappoints customers: [points] pts."},
        ],
    }],
    "kpi_weights": {"cash position": 50, "customer satisfaction": 50},
}


def test_instructor_catalog_reports_the_n_times_m_number(client):
    d = client.get("/instructor/templates").json()
    assert d["scenarios"] == len(d["templates"]) * len(d["locales"])
    assert d["templates"][0]["title"] and d["templates"][0]["options"] >= 2
    assert "freight_expedite_multiplier" in d["scale_options"]
    assert "[country]" in d["tokens"]


def test_preview_returns_every_locale_and_never_publishes(client, sandbox_templates):
    before = sorted(p.name for p in sandbox_templates.glob("*.yaml"))
    r = client.post("/instructor/drafts/preview", json=DRAFT)
    assert r.status_code == 200
    body = r.json()
    assert body["valid"] and body["template_id"] == "port_strike_delay"
    assert body["exists"] is False
    assert len(body["preview"]["locales"]) == 4
    assert sorted(p.name for p in sandbox_templates.glob("*.yaml")) == before


def test_invalid_draft_returns_one_sentence_not_a_trace(client):
    bad = dict(DRAFT, kpi_weights={"cash position": 10})
    r = client.post("/instructor/drafts/preview", json=bad)
    assert r.status_code == 422
    assert r.json()["detail"] == "KPI weights must add up to 100%, they add up to 10%"


def test_publish_then_play_end_to_end(client, sandbox_templates):
    r = client.post("/instructor/drafts/publish", json=DRAFT)
    assert r.status_code == 200 and r.json()["overwrote"] is False

    # It is in the learner catalog immediately.
    cat = client.get("/catalog").json()
    assert "port_strike_delay" in cat["templates"]
    assert cat["possible_scenarios"] == len(cat["templates"]) * len(cat["locales"])

    # And a learner can play and be scored on it, in any country.
    s = client.post("/scenarios/generate",
                    data=dict(template_id="port_strike_delay", locale="brazil", seed=2)).json()
    d = s["decisions"][0]
    r = client.post("/decisions/score", data=dict(
        template_id="port_strike_delay", locale=s["locale_id"], seed=2,
        decision_id=d["id"], choice="air_freight_a_partial_load", learner_id="ines"))
    assert r.status_code == 200
    assert r.json()["score_delta"] == -22.8  # -12 x 1.9, from the authored file alone
    assert "1.9x" in r.json()["justification"][0]


def test_publishing_twice_needs_overwrite_and_says_so_plainly(client, sandbox_templates):
    client.post("/instructor/drafts/publish", json=DRAFT)
    r = client.post("/instructor/drafts/publish", json=DRAFT)
    assert r.status_code == 409
    assert "already exists" in r.json()["detail"]
    r = client.post("/instructor/drafts/publish", json=DRAFT, params={"overwrite": True})
    assert r.status_code == 200 and r.json()["overwrote"] is True


def test_open_published_template_back_in_the_builder(client):
    d = client.get("/instructor/drafts/heatwave_demand").json()
    assert d["title"] == "Heat Wave Demand Spike"
    assert d["kpi_weights"] == {"cash_position": 40, "customer_satisfaction": 35, "overhead_cost": 25}
    assert "[country]" in d["decisions"][1]["options"][1]["reason"]
    # and it round-trips back out
    assert client.post("/instructor/drafts/preview", json=d).status_code == 200


def test_open_unknown_template_404s(client):
    assert client.get("/instructor/drafts/nope").status_code == 404


# ---- the Thief hat, pointed at the new write endpoint ----

@pytest.mark.parametrize("bad_id", ["../../../etc/passwd", "../locales/uk", "a/b", "Heatwave", "x" * 65])
def test_publish_cannot_write_outside_the_templates_folder(client, sandbox_templates, bad_id):
    r = client.post("/instructor/drafts/publish", json=dict(DRAFT, id=bad_id))
    assert r.status_code == 422, bad_id
    assert sorted(p.name for p in sandbox_templates.rglob("*.yaml")) == \
           ["heatwave_demand.yaml", "made_to_order.yaml"]


def test_publish_rejects_a_draft_that_is_not_an_object(client, sandbox_templates):
    assert client.post("/instructor/drafts/publish", json=["not", "a", "draft"]).status_code == 422


def test_published_file_always_loads_back_through_the_real_loader(client, sandbox_templates):
    """Whatever the builder writes must survive templates.load() — otherwise
    the instructor has published a scenario that 404s for learners."""
    client.post("/instructor/drafts/publish", json=DRAFT)
    assert templates.load("port_strike_delay")["title"] == "Port Strike Delay"


def test_blank_id_falls_back_to_the_title(client, sandbox_templates):
    """An instructor never types an id; blank means 'derive it from my title'."""
    r = client.post("/instructor/drafts/publish", json=dict(DRAFT, id=""))
    assert r.status_code == 200 and r.json()["published"] == "port_strike_delay"
