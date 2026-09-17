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
from datetime import date, datetime, timezone
from typing import Optional
from sqlalchemy import UniqueConstraint
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


def record_attempt(session: Session, learner_id: str, template_id: str, locale: str,
                    score: float, mistake: Optional[str] = None) -> LearnerProgress:
    locale = locale.lower()
    progress = recall(session, learner_id, template_id, locale)
    if progress is None:
        progress = LearnerProgress(learner_id=learner_id, template_id=template_id, locale=locale)
    progress.attempts += 1
    progress.best_score = max(progress.best_score, score)
    if mistake:
        progress.last_mistake = mistake
    progress.updated_at = datetime.now(timezone.utc)
    session.add(progress); session.commit(); session.refresh(progress)
    return progress


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
    """One completed sitting. This is the only thing that moves a learner's
    visible record."""
    locale = locale.lower()
    today = on_day or datetime.now(timezone.utc).date()
    progress = recall(session, learner_id, template_id, locale)
    if progress is None:
        progress = LearnerProgress(learner_id=learner_id, template_id=template_id, locale=locale)
    progress.runs_completed += 1
    progress.best_run_score = (final_score if progress.best_run_score is None
                               else max(progress.best_run_score, final_score))
    progress.current_streak = next_streak(progress.last_completed_on, today, progress.current_streak)
    progress.longest_streak = max(progress.longest_streak, progress.current_streak)
    progress.last_completed_on = today
    if mistake:
        progress.last_mistake = mistake
    progress.updated_at = datetime.now(timezone.utc)
    session.add(progress); session.commit(); session.refresh(progress)
    return progress
