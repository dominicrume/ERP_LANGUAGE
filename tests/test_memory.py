from sqlmodel import Session, SQLModel, create_engine
from erpsim import memory

engine = create_engine("sqlite:///:memory:")
SQLModel.metadata.create_all(engine)


def test_recall_none_for_new_learner():
    with Session(engine) as s:
        assert memory.recall(s, "frank", "heatwave_demand") is None


def test_attempts_increment_and_best_score_kept():
    with Session(engine) as s:
        memory.record_attempt(s, "frank", "heatwave_demand", "uk", 72.0)
        p = memory.record_attempt(s, "frank", "heatwave_demand", "uk", 88.0)
        assert p.attempts == 2
        assert p.best_score == 88.0


def test_learners_never_merge():
    with Session(engine) as s:
        memory.record_attempt(s, "frank", "heatwave_demand", "uk", 90.0)
        memory.record_attempt(s, "priya", "heatwave_demand", "uk", 10.0)
        frank = memory.recall(s, "frank", "heatwave_demand")
        priya = memory.recall(s, "priya", "heatwave_demand")
        assert frank.best_score == 90.0 and priya.best_score == 10.0
