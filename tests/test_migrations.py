"""CONTEXT.md gaps F and G: the schema had no version and no way to change
without risking learner data, and nothing stopped a duplicate learner row.

The test that matters is the last one in each pair: after migrating, is the
learner's own data still there and still correct?
"""
import sqlite3

import pytest
from sqlalchemy import inspect, text
from sqlmodel import Session, create_engine

from erpsim import memory, migrations

V04_SCHEMA = """
CREATE TABLE learnerprogress (
  id INTEGER NOT NULL PRIMARY KEY,
  learner_id VARCHAR NOT NULL,
  template_id VARCHAR NOT NULL,
  locale VARCHAR NOT NULL,
  attempts INTEGER NOT NULL,
  best_score FLOAT NOT NULL,
  last_mistake VARCHAR,
  updated_at DATETIME NOT NULL
);
"""


def _v04_database(tmp_path, rows=()):
    """A database as v0.4 left it: no version table, no run columns, no
    unique index, and real learner rows in it."""
    path = tmp_path / "old.db"
    con = sqlite3.connect(path)
    con.executescript(V04_SCHEMA)
    for row in rows:
        con.execute("INSERT INTO learnerprogress "
                    "(learner_id, template_id, locale, attempts, best_score, last_mistake, updated_at) "
                    "VALUES (?,?,?,?,?,?,?)", row)
    con.commit(); con.close()
    return create_engine(f"sqlite:///{path}")


# ---------------------------------------------------------------- versioning
def test_a_fresh_database_lands_on_the_latest_version(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/fresh.db")
    assert migrations.current_version(engine) == 0
    applied = migrations.migrate(engine)
    assert applied == [m[0] for m in migrations.MIGRATIONS]
    assert migrations.current_version(engine) == migrations.LATEST
    tables = set(inspect(engine).get_table_names())
    assert {"learnerprogress", "scenariorun", "rundecision", "schema_version"} <= tables


def test_migrating_twice_changes_nothing(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/twice.db")
    migrations.migrate(engine)
    assert migrations.migrate(engine) == []
    assert migrations.current_version(engine) == migrations.LATEST


def test_an_older_build_refuses_a_newer_database(tmp_path):
    """Better to stop than to write v1 code against a v2 database."""
    engine = create_engine(f"sqlite:///{tmp_path}/future.db")
    migrations.migrate(engine)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO schema_version (version, applied_at) VALUES (99, CURRENT_TIMESTAMP)"))
    with pytest.raises(migrations.SchemaTooNewError, match="v99"):
        migrations.migrate(engine)


# ---------------------------------------------------------------- upgrading real data
def test_a_v04_database_upgrades_and_keeps_the_learner_data(tmp_path):
    engine = _v04_database(tmp_path, rows=[
        ("frank", "heatwave_demand", "uk", 3, 88.0, "Expedite cost you.", "2026-09-16 10:00:00"),
        ("frank", "heatwave_demand", "nigeria", 1, 58.0, None, "2026-09-16 11:00:00"),
        ("priya", "made_to_order", "uk", 7, 95.0, None, "2026-09-16 12:00:00"),
    ])
    migrations.migrate(engine)

    with Session(engine) as s:
        frank_uk = memory.recall(s, "frank", "heatwave_demand", "uk")
        assert frank_uk.attempts == 3 and frank_uk.best_score == 88.0
        assert frank_uk.last_mistake == "Expedite cost you."
        # Old rows counted decisions. Calling those completed runs would be a lie.
        assert frank_uk.runs_completed == 0 and frank_uk.best_run_score is None
        assert frank_uk.current_streak == 0 and frank_uk.last_completed_on is None
        assert memory.recall(s, "frank", "heatwave_demand", "nigeria").best_score == 58.0
        assert memory.recall(s, "priya", "made_to_order", "uk").attempts == 7


def test_an_upgraded_database_can_immediately_record_a_run(tmp_path):
    engine = _v04_database(tmp_path, rows=[
        ("frank", "heatwave_demand", "uk", 3, 88.0, None, "2026-09-16 10:00:00")])
    migrations.migrate(engine)
    with Session(engine) as s:
        p = memory.record_run(s, "frank", "heatwave_demand", "uk", 76.0)
        assert p.runs_completed == 1 and p.best_run_score == 76.0 and p.current_streak == 1
        assert p.attempts == 3        # the old count is left alone, not rewritten


# ---------------------------------------------------------------- duplicates
def test_duplicate_learner_rows_are_merged_then_made_impossible(tmp_path):
    """The latent Postgres bug: two rows for one learner, the second
    invisible to every read. Existing duplicates are folded together rather
    than dropped, and the constraint stops new ones."""
    engine = _v04_database(tmp_path, rows=[
        ("frank", "heatwave_demand", "uk", 2, 70.0, "First mistake.", "2026-09-16 10:00:00"),
        ("frank", "heatwave_demand", "uk", 5, 91.0, "Later mistake.", "2026-09-16 11:00:00"),
    ])
    migrations.migrate(engine)
    with engine.begin() as conn:
        rows = conn.execute(text("SELECT attempts, best_score, last_mistake FROM learnerprogress "
                                 "WHERE learner_id='frank'")).fetchall()
    assert len(rows) == 1
    assert rows[0][0] == 7                      # 2 + 5, nothing lost
    assert rows[0][1] == 91.0                   # the better score survives
    assert rows[0][2] == "Later mistake."

    with engine.begin() as conn:
        with pytest.raises(Exception):
            conn.execute(text("INSERT INTO learnerprogress "
                              "(learner_id, template_id, locale, attempts, best_score, updated_at, "
                              " runs_completed, current_streak, longest_streak) "
                              "VALUES ('frank','heatwave_demand','uk',1,1.0,CURRENT_TIMESTAMP,0,0,0)"))


def test_a_fresh_database_refuses_duplicates_too(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/fresh.db")
    migrations.migrate(engine)
    with Session(engine) as s:
        memory.record_run(s, "amina", "heatwave_demand", "uk", 80.0)
    with engine.begin() as conn:
        with pytest.raises(Exception):
            conn.execute(text("INSERT INTO learnerprogress "
                              "(learner_id, template_id, locale, attempts, best_score, updated_at, "
                              " runs_completed, current_streak, longest_streak) "
                              "VALUES ('amina','heatwave_demand','uk',0,0.0,CURRENT_TIMESTAMP,0,0,0)"))


def test_the_unique_index_covers_exactly_the_learner_key(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/fresh.db")
    migrations.migrate(engine)
    indexes = inspect(engine).get_indexes("learnerprogress")
    unique = [i for i in indexes if i["unique"]]
    assert any(tuple(i["column_names"]) == migrations.LEARNER_KEY for i in unique), indexes
