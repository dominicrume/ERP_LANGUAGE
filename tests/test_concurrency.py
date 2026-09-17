"""Two learners finishing at the same moment must both be counted.

Found by probing the running product, not by a test: eight simultaneous
completions produced two 500-level errors and recorded two. The record was
read into Python, incremented and written back, so overlapping reads lost
each other's work, and the unique index turned the collision into an error.
Everything is now computed in SQL against the row's own values.
"""
import threading

import pytest
from sqlmodel import Session

from erpsim import main, memory, migrations


@pytest.fixture
def engine(tmp_path):
    """A file-backed database: an in-memory one cannot show a write race."""
    eng = main.make_engine(f"sqlite:///{tmp_path}/race.db")
    migrations.migrate(eng)
    return eng


def _run_in_parallel(fn, n):
    errors = []
    def wrapped(i):
        try:
            fn(i)
        except Exception as e:                       # noqa: BLE001 - the point is to catch any
            errors.append(f"{type(e).__name__}: {e}")
    threads = [threading.Thread(target=wrapped, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return errors


def test_simultaneous_completions_are_all_counted(engine):
    def finish(i):
        with Session(engine) as s:
            memory.record_run(s, "amina", "heatwave_demand", "uk", float(60 + i))

    errors = _run_in_parallel(finish, 8)
    assert errors == []
    with Session(engine) as s:
        p = memory.recall(s, "amina", "heatwave_demand", "uk")
    assert p.runs_completed == 8, "a completion was lost"
    assert p.best_run_score == 67.0, "the best score must survive the race"
    assert p.current_streak == 1 and p.longest_streak == 1


def test_simultaneous_decisions_on_the_legacy_path_are_all_counted(engine):
    def score(i):
        with Session(engine) as s:
            memory.record_attempt(s, "bo", "heatwave_demand", "uk", float(50 + i))

    assert _run_in_parallel(score, 8) == []
    with Session(engine) as s:
        p = memory.recall(s, "bo", "heatwave_demand", "uk")
    assert p.attempts == 8 and p.best_score == 57.0


def test_a_race_still_leaves_exactly_one_row(engine):
    def finish(i):
        with Session(engine) as s:
            memory.record_run(s, "cleo", "heatwave_demand", "brazil", 70.0)

    _run_in_parallel(finish, 6)
    with Session(engine) as s:
        rows = memory.recall_all(s, "cleo", "heatwave_demand")
    assert len(rows) == 1 and rows[0].runs_completed == 6


def test_different_learners_in_parallel_do_not_collide(engine):
    def finish(i):
        with Session(engine) as s:
            memory.record_run(s, f"learner_{i}", "heatwave_demand", "uk", 80.0)

    assert _run_in_parallel(finish, 8) == []
    with Session(engine) as s:
        for i in range(8):
            p = memory.recall(s, f"learner_{i}", "heatwave_demand", "uk")
            assert p.runs_completed == 1, i
