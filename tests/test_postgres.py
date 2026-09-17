"""SCALING.md #1 says SQLite for development, Postgres for real, and that
the difference is a DSN swap. That was asserted for a year and never run.

These tests run the real thing against a real Postgres when
ERPSIM_TEST_POSTGRES_URL is set, which CI always does. They skip loudly
otherwise: a skip means unproven, not proven.
"""
import os

import pytest
from sqlalchemy import inspect, text
from sqlmodel import Session

from erpsim import main, memory, migrations

POSTGRES_URL = os.environ.get("ERPSIM_TEST_POSTGRES_URL")
pytestmark = pytest.mark.skipif(not POSTGRES_URL,
                                reason="set ERPSIM_TEST_POSTGRES_URL to run the Postgres proof")


@pytest.fixture
def pg_engine():
    engine = main.make_engine(POSTGRES_URL)
    with engine.begin() as conn:
        for table in ("rundecision", "scenariorun", "learnerprogress", "schema_version"):
            conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
    yield engine
    engine.dispose()


def test_the_schema_builds_on_postgres_from_nothing(pg_engine):
    applied = migrations.migrate(pg_engine)
    assert applied == [m[0] for m in migrations.MIGRATIONS]
    tables = set(inspect(pg_engine).get_table_names())
    assert {"learnerprogress", "scenariorun", "rundecision", "schema_version"} <= tables
    assert migrations.migrate(pg_engine) == []          # idempotent here too


def test_the_unique_learner_key_is_enforced_by_postgres(pg_engine):
    migrations.migrate(pg_engine)
    with Session(pg_engine) as s:
        memory.record_run(s, "amina", "heatwave_demand", "uk", 80.0)
    with pytest.raises(Exception):
        with pg_engine.begin() as conn:
            conn.execute(text(
                "INSERT INTO learnerprogress (learner_id, template_id, locale, attempts, "
                "best_score, runs_completed, current_streak, longest_streak, updated_at) "
                "VALUES ('amina','heatwave_demand','uk',0,0,0,0,0, NOW())"))


def test_records_and_streaks_behave_the_same_on_postgres(pg_engine):
    from datetime import date
    migrations.migrate(pg_engine)
    with Session(pg_engine) as s:
        memory.record_run(s, "bo", "heatwave_demand", "brazil", 70.0, on_day=date(2026, 9, 15))
        memory.record_run(s, "bo", "heatwave_demand", "brazil", 91.0, mistake="Expedite cost you.",
                          on_day=date(2026, 9, 16))
        p = memory.record_run(s, "bo", "heatwave_demand", "brazil", 55.0, on_day=date(2026, 9, 18))
    assert p.runs_completed == 3
    assert p.best_run_score == 91.0        # the best survives a worse later run
    assert p.current_streak == 1           # 17 September was missed
    assert p.longest_streak == 2
    assert p.last_mistake == "Expedite cost you."


def test_simultaneous_completions_are_all_counted_on_postgres(pg_engine):
    """The race that lost six of eight sittings on SQLite. Postgres is where
    it would really have bitten, because writers genuinely interleave."""
    import threading
    migrations.migrate(pg_engine)
    errors = []

    def finish(i):
        try:
            with Session(pg_engine) as s:
                memory.record_run(s, "cleo", "heatwave_demand", "uk", float(60 + i))
        except Exception as e:                           # noqa: BLE001
            errors.append(f"{type(e).__name__}: {e}")

    threads = [threading.Thread(target=finish, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    with Session(pg_engine) as s:
        p = memory.recall(s, "cleo", "heatwave_demand", "uk")
    assert p.runs_completed == 8
    assert p.best_run_score == 67.0


def test_a_whole_sitting_plays_through_the_api_against_postgres(pg_engine, monkeypatch):
    from fastapi.testclient import TestClient
    migrations.migrate(pg_engine)
    monkeypatch.setattr(main, "engine", pg_engine)
    with TestClient(main.app) as c:
        started = c.post("/runs", data={"template_id": "heatwave_demand", "locale": "brazil",
                                        "seed": 1, "learner_id": "dara"}).json()
        run_id = started["run"]["run_id"]
        for decision in started["scenario"]["decisions"]:
            r = c.post(f"/runs/{run_id}/decisions",
                       data={"decision_id": decision["id"], "choice": decision["options"][0],
                             "learner_id": "dara"})
            assert r.status_code == 200, r.text
        summary = c.post(f"/runs/{run_id}/complete", data={"learner_id": "dara"}).json()
        assert 0.0 <= summary["final_score"] <= 100.0
        assert summary["record"]["runs_completed"] == 1
        progress = c.get("/learners/dara/progress/heatwave_demand?locale=brazil").json()
        assert progress["best_run_score"] == summary["final_score"]
