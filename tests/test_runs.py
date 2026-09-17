"""A run is one sitting of one scenario: it starts, it accumulates, it ends.

These tests close CONTEXT.md gaps A (the score discarded earlier decisions),
B (a record counted clicks) and D (nothing ever finished), and they hold the
BREAK.md Thief line: nobody plays in someone else's run, nobody answers
twice, nobody finishes early.
"""
import pytest


TPL = "heatwave_demand"


def _start(client, **over):
    data = {"template_id": TPL, "locale": "uk", "seed": 1}
    data.update(over)
    r = client.post("/runs", data=data)
    assert r.status_code == 200, r.text
    return r.json()


def _decide(client, run_id, decision_id, choice, **over):
    data = {"decision_id": decision_id, "choice": choice}
    data.update(over)
    return client.post(f"/runs/{run_id}/decisions", data=data)


def _play_all(client, run_id, choices, learner_id=None):
    out = []
    for decision_id, choice in choices.items():
        extra = {"learner_id": learner_id} if learner_id else {}
        r = _decide(client, run_id, decision_id, choice, **extra)
        assert r.status_code == 200, r.text
        out.append(r.json())
    return out


# ---------------------------------------------------------------- starting
def test_a_run_starts_with_its_scenario_and_nothing_answered(client):
    body = _start(client, learner_id="amina")
    run, scenario = body["run"], body["scenario"]
    assert run["run_id"] and run["learner_id"] == "amina"
    assert run["decisions_answered"] == 0
    assert run["decisions_total"] == len(scenario["decisions"]) == 2
    assert run["score_so_far"] == 100.0 and run["complete"] is False
    assert scenario["locale_id"] == "uk"


def test_starting_a_run_for_a_scenario_that_does_not_exist_is_404(client):
    assert client.post("/runs", data={"template_id": "nope", "locale": "uk", "seed": 1}).status_code == 404
    assert client.post("/runs", data={"template_id": TPL, "locale": "atlantis", "seed": 1}).status_code == 404


# ---------------------------------------------------------------- the score
def test_the_score_is_cumulative_across_the_whole_run(client):
    """CONTEXT.md gap A, the defect this module exists to fix: +8 then -32
    is 76, not 68. Before runs, the second decision overwrote the first."""
    run = _start(client, learner_id="amina")["run"]
    first = _decide(client, run["run_id"], "customer_allocation", "highest_value_first",
                    learner_id="amina").json()
    second = _decide(client, run["run_id"], "freight_choice", "expedite", learner_id="amina").json()
    assert first["score_delta"] == 8 and second["score_delta"] == -32
    assert first["score_so_far"] == 100.0        # 108 clamped: nobody scores above 100
    assert first["raw_score_so_far"] == 108.0
    assert second["score_so_far"] == 76.0        # 100 + 8 - 32, the honest total
    assert second["decisions_answered"] == 2 and second["remaining_decision_ids"] == []


def test_a_run_score_never_leaves_nought_to_a_hundred(client):
    run = _start(client, locale="nigeria")["run"]
    _play_all(client, run["run_id"], {"customer_allocation": "first_come_first_served",
                                      "freight_choice": "expedite"})
    body = client.post(f"/runs/{run['run_id']}/complete").json()
    assert body["raw_score_so_far"] == 58.0
    assert 0.0 <= body["final_score"] <= 100.0


def test_every_decision_keeps_the_reason_that_produced_it(client):
    run = _start(client, locale="brazil")["run"]
    _play_all(client, run["run_id"], {"customer_allocation": "strategic_accounts_first",
                                      "freight_choice": "expedite"})
    body = client.get(f"/runs/{run['run_id']}").json()["run"]
    assert all(d["justification"] for d in body["decisions"])
    assert "1.9x" in body["decisions"][1]["justification"][0]


# ---------------------------------------------------------------- finishing
def test_a_run_finishes_with_a_final_score_and_the_costliest_decision(client):
    run = _start(client, learner_id="amina")["run"]
    _play_all(client, run["run_id"], {"customer_allocation": "highest_value_first",
                                      "freight_choice": "expedite"}, learner_id="amina")
    r = client.post(f"/runs/{run['run_id']}/complete", data={"learner_id": "amina"})
    assert r.status_code == 200
    body = r.json()
    assert body["complete"] is True and body["final_score"] == 76.0
    assert body["completed_at"]
    assert body["biggest_mistake"]["decision_id"] == "freight_choice"
    assert "1.6x" in body["biggest_mistake"]["why"]


def test_a_clean_run_reports_no_mistake(client):
    run = _start(client)["run"]
    _play_all(client, run["run_id"], {"customer_allocation": "highest_value_first",
                                      "freight_choice": "standard"})
    assert client.post(f"/runs/{run['run_id']}/complete").json()["biggest_mistake"] is None


def test_a_run_cannot_be_finished_early(client):
    run = _start(client)["run"]
    _decide(client, run["run_id"], "freight_choice", "standard")
    r = client.post(f"/runs/{run['run_id']}/complete")
    assert r.status_code == 422
    assert "customer_allocation" in r.json()["detail"]


def test_a_run_cannot_be_finished_twice(client):
    run = _start(client)["run"]
    _play_all(client, run["run_id"], {"customer_allocation": "highest_value_first",
                                      "freight_choice": "standard"})
    assert client.post(f"/runs/{run['run_id']}/complete").status_code == 200
    r = client.post(f"/runs/{run['run_id']}/complete")
    assert r.status_code == 409 and "already complete" in r.json()["detail"]


# ---------------------------------------------------------------- the Thief hat
def test_the_same_decision_cannot_be_answered_twice(client):
    """Replaying a decision was how a record could be inflated."""
    run = _start(client)["run"]
    assert _decide(client, run["run_id"], "freight_choice", "standard").status_code == 200
    r = _decide(client, run["run_id"], "freight_choice", "expedite")
    assert r.status_code == 409 and "already been answered" in r.json()["detail"]
    assert client.get(f"/runs/{run['run_id']}").json()["run"]["decisions_answered"] == 1


def test_no_decisions_after_the_run_is_complete(client):
    run = _start(client)["run"]
    _play_all(client, run["run_id"], {"customer_allocation": "highest_value_first",
                                      "freight_choice": "standard"})
    client.post(f"/runs/{run['run_id']}/complete")
    r = _decide(client, run["run_id"], "freight_choice", "expedite")
    assert r.status_code == 409


def test_one_learner_cannot_play_or_finish_another_learners_run(client):
    run = _start(client, learner_id="amina")["run"]
    assert _decide(client, run["run_id"], "freight_choice", "standard",
                   learner_id="mallory").status_code == 403
    assert _decide(client, run["run_id"], "freight_choice", "standard").status_code == 403
    _decide(client, run["run_id"], "freight_choice", "standard", learner_id="amina")
    _decide(client, run["run_id"], "customer_allocation", "highest_value_first", learner_id="amina")
    assert client.post(f"/runs/{run['run_id']}/complete",
                       data={"learner_id": "mallory"}).status_code == 403


def test_an_anonymous_run_cannot_be_claimed_by_a_name(client):
    run = _start(client)["run"]
    assert run["learner_id"] is None
    assert _decide(client, run["run_id"], "freight_choice", "standard",
                   learner_id="mallory").status_code == 403
    assert _decide(client, run["run_id"], "freight_choice", "standard").status_code == 200


def test_a_forged_or_unknown_run_id_is_404(client):
    for bad in ("deadbeef", "../../etc/passwd", "x" * 80):
        assert client.get(f"/runs/{bad}").status_code == 404
        assert _decide(client, bad, "freight_choice", "standard").status_code == 404
        assert client.post(f"/runs/{bad}/complete").status_code == 404


def test_a_decision_or_choice_outside_the_scenario_is_refused(client):
    run = _start(client)["run"]
    assert _decide(client, run["run_id"], "not_a_decision", "standard").status_code == 422
    assert _decide(client, run["run_id"], "freight_choice", "TELEPORT").status_code == 422
    assert client.get(f"/runs/{run['run_id']}").json()["run"]["decisions_answered"] == 0


# ---------------------------------------------------------------- resuming
def test_a_run_can_be_reloaded_and_carried_on(client):
    """BREAK.md Firefighter: losing the connection mid-scenario must not
    lose the sitting, because the run lives on the server."""
    run = _start(client, learner_id="amina")["run"]
    _decide(client, run["run_id"], "customer_allocation", "highest_value_first", learner_id="amina")
    reloaded = client.get(f"/runs/{run['run_id']}").json()
    assert reloaded["run"]["decisions_answered"] == 1
    assert reloaded["run"]["remaining_decision_ids"] == ["freight_choice"]
    assert reloaded["run"]["score_so_far"] == 100.0
    assert reloaded["scenario"]["title"] == "Heat Wave Demand Spike"
    r = _decide(client, run["run_id"], "freight_choice", "expedite", learner_id="amina")
    assert r.status_code == 200 and r.json()["score_so_far"] == 76.0


def test_the_scenario_a_run_replays_is_always_the_one_that_was_played(client):
    """The scenario is regenerated from template, locale and seed, so the
    story and product never drift between visits (ENGINEERING.md #3)."""
    body = _start(client, seed=7)
    first = body["scenario"]["narrative"]
    again = client.get(f"/runs/{body['run']['run_id']}").json()["scenario"]["narrative"]
    assert first == again


@pytest.mark.parametrize("locale,expected", [("uk", 68.0), ("germany", 70.0),
                                             ("nigeria", 58.0), ("brazil", 62.0)])
def test_the_same_run_in_four_countries_ends_on_four_different_scores(client, locale, expected):
    """The localization thesis, now measured on a whole sitting."""
    run = _start(client, locale=locale)["run"]
    _play_all(client, run["run_id"], {"customer_allocation": "first_come_first_served",
                                      "freight_choice": "expedite"})
    assert client.post(f"/runs/{run['run_id']}/complete").json()["final_score"] == expected
