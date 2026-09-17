"""Persistent learner memory (Rule 5): one row per learner x template x
locale, never merged across learners, never guessed. This is the "AI tutor
remembers you across sessions" promise.

A record counts completed runs, not clicks. `attempts` and `best_score`
still count individual decisions scored through the older stateless
endpoint, and are kept so nothing published before v1.0 silently changes
meaning; everything a learner is shown comes from the run columns.

Streak rule, stated here because a learner is told it in the product:
a streak is the number of consecutive calendar days on which the learner
completed at least one run. Two runs in a day do not raise it. Missing a
day resets it to 1 on the next completion."""
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import UniqueConstraint, text
from sqlmodel import Field, Session, SQLModel, select


class LearnerProgress(SQLModel, table=True):
    # One row per learner per template per country, enforced by the database
    # so two interleaved writes cannot create a second, invisible record.
    __table_args__ = (UniqueConstraint("learner_id", "template_id", "locale",
                                       name="ix_learnerprogress_learner_template_locale"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    learner_id: str = Field(index=True)
    template_id: str = Field(index=True)
    locale: str = Field(index=True)
    attempts: int = 0                      # decisions scored outside a run (legacy path)
    best_score: float = 0.0                # best single decision (legacy path)
    runs_completed: int = 0                # sittings played start to finish
    best_run_score: Optional[float] = None # best completed run, out of 100
    current_streak: int = 0
    longest_streak: int = 0
    last_completed_on: Optional[date] = None
    last_mistake: Optional[str] = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def recall(session: Session, learner_id: str, template_id: str, locale: str) -> Optional[LearnerProgress]:
    """One learner, one template, one country. A UK attempt never counts
    toward a Nigeria best score — the rules that produced them differ."""
    stmt = select(LearnerProgress).where(
        LearnerProgress.learner_id == learner_id,
        LearnerProgress.template_id == template_id,
        LearnerProgress.locale == locale.lower(),
    )
    return session.exec(stmt).first()


def recall_all(session: Session, learner_id: str, template_id: str) -> list[LearnerProgress]:
    """Every locale this learner has attempted for one template. Still one
    learner only — cross-learner queries do not exist in this module."""
    stmt = select(LearnerProgress).where(
        LearnerProgress.learner_id == learner_id,
        LearnerProgress.template_id == template_id,
    ).order_by(LearnerProgress.locale)
    return list(session.exec(stmt))


KEY = "learner_id = :learner AND template_id = :template AND locale = :locale"


def _ensure_row(session: Session, learner_id: str, template_id: str, locale: str) -> None:
    """Create the row if it is not there, without racing another writer.
    ON CONFLICT DO NOTHING is understood by both SQLite and Postgres, so two
    simultaneous first-finishers cannot both insert."""
    session.execute(text(
        "INSERT INTO learnerprogress "
        "(learner_id, template_id, locale, attempts, best_score, runs_completed, "
        " current_streak, longest_streak, updated_at) "
        "VALUES (:learner, :template, :locale, 0, 0.0, 0, 0, 0, :now) "
        "ON CONFLICT DO NOTHING"),
        {"learner": learner_id, "template": template_id, "locale": locale,
         "now": datetime.now(timezone.utc)})


def record_attempt(session: Session, learner_id: str, template_id: str, locale: str,
                    score: float, mistake: Optional[str] = None) -> LearnerProgress:
    """Legacy path: one decision scored outside a run. Counted in SQL so two
    writers cannot both read the same total and both write it back."""
    locale = locale.lower()
    _ensure_row(session, learner_id, template_id, locale)
    session.execute(text(
        f"UPDATE learnerprogress SET attempts = attempts + 1, "
        f"best_score = CASE WHEN best_score < :score THEN :score ELSE best_score END, "
        f"last_mistake = COALESCE(:mistake, last_mistake), updated_at = :now WHERE {KEY}"),
        {"score": score, "mistake": mistake, "now": datetime.now(timezone.utc),
         "learner": learner_id, "template": template_id, "locale": locale})
    session.commit()
    return recall(session, learner_id, template_id, locale)


def next_streak(previous_day: Optional[date], today: date, current: int) -> int:
    """Consecutive calendar days with at least one completed run."""
    if previous_day is None:
        return 1
    gap = (today - previous_day).days
    if gap <= 0:
        return max(current, 1)      # already counted today
    if gap == 1:
        return current + 1
    return 1                        # a day was missed


def record_run(session: Session, learner_id: str, template_id: str, locale: str,
               final_score: float, mistake: Optional[str] = None,
               on_day: Optional[date] = None) -> LearnerProgress:
    """One completed sitting. The only thing that moves a learner's visible
    record.

    Every field is computed in SQL against the row's own current values, so
    two sittings finishing at the same moment both count. Doing this in
    Python meant reading, adding one, and writing back, which lost one of
    the two whenever the reads overlapped.
    """
    locale = locale.lower()
    today = on_day or datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)
    params = {"score": final_score, "mistake": mistake, "today": today, "yesterday": yesterday,
              "now": datetime.now(timezone.utc),
              "learner": learner_id, "template": template_id, "locale": locale}

    _ensure_row(session, learner_id, template_id, locale)
    # The streak rule, in SQL: same day holds, the next day adds one, a gap
    # starts again at one. (See next_streak, which states the same rule for
    # the tests and for anyone reading this module.)
    session.execute(text(
        f"UPDATE learnerprogress SET "
        f"  runs_completed = runs_completed + 1, "
        f"  best_run_score = CASE WHEN best_run_score IS NULL OR best_run_score < :score "
        f"                        THEN :score ELSE best_run_score END, "
        f"  current_streak = CASE "
        f"      WHEN last_completed_on IS NULL THEN 1 "
        f"      WHEN last_completed_on = :today THEN CASE WHEN current_streak < 1 THEN 1 ELSE current_streak END "
        f"      WHEN last_completed_on = :yesterday THEN current_streak + 1 "
        f"      ELSE 1 END, "
        f"  last_completed_on = :today, "
        f"  last_mistake = COALESCE(:mistake, last_mistake), "
        f"  updated_at = :now "
        f"WHERE {KEY}"), params)
    session.execute(text(
        f"UPDATE learnerprogress SET longest_streak = current_streak "
        f"WHERE {KEY} AND current_streak > longest_streak"), params)
    session.commit()
    return recall(session, learner_id, template_id, locale)
