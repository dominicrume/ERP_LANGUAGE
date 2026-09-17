"""HTTP contract tests: the loud-failure guarantees of BREAK.md #3 and #4,
checked at the API boundary where a learner would actually hit them."""


def _score(client, **overrides):
    data = dict(template_id="heatwave_demand", locale="uk", seed=1,
                decision_id="freight_choice", choice="standard")
    data.update(overrides)
    return client.post("/decisions/score", data=data)


def test_valid_choice_scores(client):
    r = _score(client, choice="expedite")
    assert r.status_code == 200
    assert r.json()["score_delta"] < 0


def test_invalid_choice_is_rejected_loud(client):
    """BREAK.md #3: a choice not in the template's options must 422, never
    silently score as something else."""
    r = _score(client, choice="TELEPORT", learner_id="probe")
    assert r.status_code == 422
    assert "TELEPORT" in r.json()["detail"]
    assert "standard" in r.json()["detail"]


def test_invalid_choice_never_touches_memory(client):
    _score(client, choice="TELEPORT", learner_id="probe")
    p = client.get("/learners/probe/progress/heatwave_demand").json()
    assert p["attempts"] == 0


def test_invalid_decision_id_is_rejected_loud(client):
    r = _score(client, decision_id="not_a_decision")
    assert r.status_code == 422


def test_unknown_locale_404s_at_api(client):
    r = _score(client, locale="atlantis")
    assert r.status_code == 404


def test_progress_is_per_locale_at_api(client):
    """Fix 3: progress endpoint reports per locale and never merges them."""
    _score(client, locale="uk", choice="standard", learner_id="frank")
    _score(client, locale="nigeria", choice="expedite", learner_id="frank")
    uk = client.get("/learners/frank/progress/heatwave_demand", params={"locale": "uk"}).json()
    ng = client.get("/learners/frank/progress/heatwave_demand", params={"locale": "nigeria"}).json()
    assert uk["attempts"] == 1 and uk["best_score"] == 100.0
    assert ng["attempts"] == 1 and ng["best_score"] < 100.0
    total = client.get("/learners/frank/progress/heatwave_demand").json()
    assert total["attempts"] == 2
    assert {r["locale"] for r in total["by_locale"]} == {"uk", "nigeria"}


def test_progress_unknown_locale_is_empty_not_error(client):
    r = client.get("/learners/frank/progress/heatwave_demand", params={"locale": "brazil"})
    assert r.status_code == 200 and r.json()["attempts"] == 0


def test_every_generated_scenario_can_be_scored_back_through_the_api(client):
    """Fix 3b: the scenario must hand the client the locale identifier the
    API accepts. Before this fix the payload only carried the display code
    (BR, DE, NG), so scoring any non-UK scenario 404'd on the first card."""
    catalog = client.get("/catalog").json()
    for t in catalog["templates"]:
        for l in catalog["locales"]:
            s = client.post("/scenarios/generate", data=dict(template_id=t, locale=l, seed=1)).json()
            assert s["locale_id"] == l
            d = s["decisions"][0]
            r = client.post("/decisions/score", data=dict(
                template_id=s["template_id"], locale=s["locale_id"], seed=s["seed"],
                decision_id=d["id"], choice=d["options"][0], learner_id="roundtrip"))
            assert r.status_code == 200, (t, l, r.text)
    p = client.get("/learners/roundtrip/progress/heatwave_demand").json()
    assert {r["locale"] for r in p["by_locale"]} == set(catalog["locales"])


def test_negative_decision_records_last_mistake(client):
    """Fix 4: PRODUCT.md #4 — 'here's what tripped you up last time' must
    be real, citing the locale rule that produced the penalty."""
    _score(client, choice="expedite", learner_id="frank")
    p = client.get("/learners/frank/progress/heatwave_demand", params={"locale": "uk"}).json()
    assert p["last_mistake"] and "1.6x" in p["last_mistake"]


def test_positive_decision_does_not_write_a_mistake(client):
    _score(client, decision_id="customer_allocation", choice="highest_value_first", learner_id="frank")
    p = client.get("/learners/frank/progress/heatwave_demand", params={"locale": "uk"}).json()
    assert p["attempts"] == 1 and p["last_mistake"] is None


# ---- Fix 11: Thief hat residue — ids are names/stems, never paths ----

def test_blank_learner_id_is_rejected(client):
    assert _score(client, learner_id="   ").status_code == 422


def test_overlong_learner_id_is_rejected(client):
    assert _score(client, learner_id="x" * 65).status_code == 422
    assert _score(client, learner_id="x" * 64).status_code == 200


def test_learner_id_with_slash_is_rejected(client):
    assert _score(client, learner_id="a/b").status_code == 422


def test_learner_id_is_trimmed_so_one_person_is_one_record(client):
    _score(client, learner_id="  frank ")
    _score(client, learner_id="frank")
    assert client.get("/learners/frank/progress/heatwave_demand", params={"locale": "uk"}).json()["attempts"] == 2


def test_path_traversal_ids_404_without_touching_the_filesystem(client):
    for tid in ("../../pyproject", "../locales/uk", "Heatwave_Demand", "a" * 65):
        assert client.post("/scenarios/generate", data=dict(template_id=tid, locale="uk", seed=1)).status_code == 404, tid
    for lid in ("../../pyproject", "../templates/heatwave_demand", "u k"):
        assert client.post("/scenarios/generate", data=dict(template_id="heatwave_demand", locale=lid, seed=1)).status_code == 404, lid
