"""Persistent learner memory (Rule 5): per learner x template, never merged,
never guessed. This is the "AI tutor remembers you across sessions" promise."""
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, Session, SQLModel, select


class LearnerProgress(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    learner_id: str
    template_id: str
    locale: str
    attempts: int = 0
    best_score: float = 0.0
    last_mistake: Optional[str] = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def recall(session: Session, learner_id: str, template_id: str) -> Optional[LearnerProgress]:
    stmt = select(LearnerProgress).where(
        LearnerProgress.learner_id == learner_id, LearnerProgress.template_id == template_id
    )
    return session.exec(stmt).first()


def record_attempt(session: Session, learner_id: str, template_id: str, locale: str,
                    score: float, mistake: Optional[str] = None) -> LearnerProgress:
    progress = recall(session, learner_id, template_id)
    if progress is None:
        progress = LearnerProgress(learner_id=learner_id, template_id=template_id, locale=locale)
    progress.attempts += 1
    progress.best_score = max(progress.best_score, score)
    if mistake:
        progress.last_mistake = mistake
    progress.updated_at = datetime.now(timezone.utc)
    session.add(progress); session.commit(); session.refresh(progress)
    return progress
