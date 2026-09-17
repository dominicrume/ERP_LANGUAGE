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
