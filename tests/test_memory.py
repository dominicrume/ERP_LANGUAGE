import pytest
from sqlmodel import Session, SQLModel, create_engine
from erpsim import memory


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def test_recall_none_for_new_learner(session):
    assert memory.recall(session, "frank", "heatwave_demand", "uk") is None
    assert memory.recall_all(session, "frank", "heatwave_demand") == []


def test_attempts_increment_and_best_score_kept(session):
    memory.record_attempt(session, "frank", "heatwave_demand", "uk", 72.0)
    p = memory.record_attempt(session, "frank", "heatwave_demand", "uk", 88.0)
    assert p.attempts == 2
    assert p.best_score == 88.0


def test_learners_never_merge(session):
    memory.record_attempt(session, "frank", "heatwave_demand", "uk", 90.0)
    memory.record_attempt(session, "priya", "heatwave_demand", "uk", 10.0)
    frank = memory.recall(session, "frank", "heatwave_demand", "uk")
    priya = memory.recall(session, "priya", "heatwave_demand", "uk")
    assert frank.best_score == 90.0 and priya.best_score == 10.0


def test_locales_never_merge(session):
    """Fix 3: a UK attempt and a Nigeria attempt are different lessons."""
    memory.record_attempt(session, "frank", "heatwave_demand", "uk", 90.0)
    memory.record_attempt(session, "frank", "heatwave_demand", "nigeria", 40.0)
    uk = memory.recall(session, "frank", "heatwave_demand", "uk")
    ng = memory.recall(session, "frank", "heatwave_demand", "nigeria")
    assert uk.attempts == 1 and uk.best_score == 90.0
    assert ng.attempts == 1 and ng.best_score == 40.0
    assert [r.locale for r in memory.recall_all(session, "frank", "heatwave_demand")] == ["nigeria", "uk"]


def test_locale_key_is_case_insensitive(session):
    memory.record_attempt(session, "frank", "heatwave_demand", "UK", 50.0)
    assert memory.recall(session, "frank", "heatwave_demand", "uk").attempts == 1


def test_last_mistake_is_kept_until_a_new_one(session):
    """Fix 4: a mistake persists across a later clean attempt."""
    memory.record_attempt(session, "frank", "heatwave_demand", "uk", 68.0, "Expedite cost you 32 pts.")
    memory.record_attempt(session, "frank", "heatwave_demand", "uk", 100.0)
    assert memory.recall(session, "frank", "heatwave_demand", "uk").last_mistake == "Expedite cost you 32 pts."


# ---- completed runs, streaks and the honest record (PROMPT-02 item 3) ----

from datetime import date  # noqa: E402

from erpsim.memory import next_streak  # noqa: E402


def test_a_record_counts_completed_runs_not_clicks(session):
    memory.record_run(session, "amina", "heatwave_demand", "uk", 76.0)
    memory.record_run(session, "amina", "heatwave_demand", "uk", 92.4)
    p = memory.recall(session, "amina", "heatwave_demand", "uk")
    assert p.runs_completed == 2
    assert p.best_run_score == 92.4
    assert p.attempts == 0            # decisions are not runs


def test_a_best_run_is_never_above_a_hundred(session):
    memory.record_run(session, "amina", "heatwave_demand", "uk", 100.0)
    assert memory.recall(session, "amina", "heatwave_demand", "uk").best_run_score <= 100.0


def test_runs_do_not_merge_across_locales_or_learners(session):
    memory.record_run(session, "amina", "heatwave_demand", "uk", 90.0)
    memory.record_run(session, "amina", "heatwave_demand", "nigeria", 50.0)
    memory.record_run(session, "bo", "heatwave_demand", "uk", 10.0)
    assert memory.recall(session, "amina", "heatwave_demand", "uk").best_run_score == 90.0
    assert memory.recall(session, "amina", "heatwave_demand", "nigeria").best_run_score == 50.0
    assert memory.recall(session, "bo", "heatwave_demand", "uk").best_run_score == 10.0


@pytest.mark.parametrize("previous,today,current,expected", [
    (None, date(2026, 9, 17), 0, 1),                       # first ever completion
    (date(2026, 9, 17), date(2026, 9, 17), 3, 3),          # a second run the same day
    (date(2026, 9, 17), date(2026, 9, 18), 3, 4),          # the next day
    (date(2026, 9, 17), date(2026, 9, 19), 3, 1),          # a day was missed
    (date(2026, 9, 30), date(2026, 10, 1), 5, 6),          # across a month end
    (date(2026, 12, 31), date(2027, 1, 1), 2, 3),          # across a year end
    (date(2026, 2, 28), date(2026, 3, 1), 4, 5),           # non-leap February
])
def test_the_streak_rule_at_its_boundaries(previous, today, current, expected):
    assert next_streak(previous, today, current) == expected


def test_a_streak_grows_day_by_day_and_resets_after_a_gap(session):
    for day, expected in [(date(2026, 9, 15), 1), (date(2026, 9, 16), 2), (date(2026, 9, 17), 3)]:
        p = memory.record_run(session, "amina", "heatwave_demand", "uk", 80.0, on_day=day)
        assert p.current_streak == expected
    p = memory.record_run(session, "amina", "heatwave_demand", "uk", 80.0, on_day=date(2026, 9, 20))
    assert p.current_streak == 1
    assert p.longest_streak == 3      # the best run of days is remembered


def test_two_runs_in_one_day_do_not_inflate_a_streak(session):
    memory.record_run(session, "amina", "heatwave_demand", "uk", 80.0, on_day=date(2026, 9, 17))
    p = memory.record_run(session, "amina", "heatwave_demand", "uk", 85.0, on_day=date(2026, 9, 17))
    assert p.current_streak == 1 and p.runs_completed == 2


def test_a_mistake_is_kept_until_a_new_one(session):
    memory.record_run(session, "amina", "heatwave_demand", "uk", 60.0, mistake="Expedite cost you.")
    memory.record_run(session, "amina", "heatwave_demand", "uk", 95.0)
    assert memory.recall(session, "amina", "heatwave_demand", "uk").last_mistake == "Expedite cost you."
