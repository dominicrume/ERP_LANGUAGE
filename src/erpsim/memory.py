"""Persistent learner memory (Rule 5): one row per learner x template x
locale, never merged across learners, never guessed. This is the "AI tutor
remembers you across sessions" promise."""
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, Session, SQLModel, select


class LearnerProgress(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    learner_id: str = Field(index=True)
    template_id: str = Field(index=True)
    locale: str = Field(index=True)
    attempts: int = 0
    best_score: float = 0.0
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
