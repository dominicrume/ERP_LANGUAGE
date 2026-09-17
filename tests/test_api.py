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
