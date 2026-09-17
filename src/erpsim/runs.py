"""A scenario run: one learner, one sitting, start to finish.

Before this module a decision was scored on its own and nothing joined the
decisions together, so the score a learner saw discarded every earlier
choice and a scenario never ended (CONTEXT.md gaps A, B, D).

A run is deterministic data plus the decisions made against it: the
scenario itself is never stored, it is regenerated from
`template_id + locale + seed` (ENGINEERING.md #3), so a run can never drift
from the scenario the learner actually played.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlmodel import Field, Session, SQLModel, select

from . import scoring

BASE_SCORE = 100.0


class RunError(ValueError):
    """Base class. Each subclass maps to one HTTP status in main.py."""


class UnknownRunError(RunError):
    """No such run (404)."""


class RunOwnershipError(RunError):
    """This run belongs to another learner (403)."""


class RunConflictError(RunError):
    """The run is not in a state where this is allowed (409)."""


class RunIncompleteError(RunError):
    """Every decision must be answered first (422)."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ScenarioRun(SQLModel, table=True):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex, primary_key=True)
    learner_id: Optional[str] = Field(default=None, index=True)
    template_id: str = Field(index=True)
    locale: str = Field(index=True)
    seed: int
    started_at: datetime = Field(default_factory=_now)
    completed_at: Optional[datetime] = None
    final_score: Optional[float] = None


class RunDecision(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: str = Field(index=True, foreign_key="scenariorun.id")
    decision_id: str
    choice: str
    score_delta: float
    justification: str = "[]"          # JSON list, kept verbatim (Rule 8)
    decided_at: datetime = Field(default_factory=_now)

    @property
    def reasons(self) -> List[str]:
        try:
            return json.loads(self.justification)
        except ValueError:                       # pragma: no cover - defensive
            return []


def clamp(score: float) -> float:
    """A learner's score is out of 100. Above or below that means nothing."""
    return round(min(100.0, max(0.0, score)), 1)


# ---------------------------------------------------------------- reading
def get(session: Session, run_id: str) -> ScenarioRun:
    run = session.get(ScenarioRun, run_id)
    if run is None:
        raise UnknownRunError(f"no run '{run_id}'")
    return run


def decisions_of(session: Session, run_id: str) -> List[RunDecision]:
    stmt = select(RunDecision).where(RunDecision.run_id == run_id).order_by(RunDecision.id)
    return list(session.exec(stmt))


def check_owner(run: ScenarioRun, learner_id: Optional[str]) -> None:
    """A named run belongs to that learner. An anonymous run belongs to
    whoever holds its id, and can never be claimed by a name later."""
    if run.learner_id != (learner_id or None):
        raise RunOwnershipError("this run belongs to another learner")


def raw_total(decisions: List[RunDecision]) -> float:
    return BASE_SCORE + sum(d.score_delta for d in decisions)


def state(session: Session, run: ScenarioRun, scenario: Dict[str, Any]) -> Dict[str, Any]:
    made = decisions_of(session, run.id)
    answered = {d.decision_id for d in made}
    remaining = [d["id"] for d in scenario["decisions"] if d["id"] not in answered]
    return {
        "run_id": run.id,
        "learner_id": run.learner_id,
        "template_id": run.template_id,
        "locale": run.locale,
        "seed": run.seed,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
        "decisions_total": len(scenario["decisions"]),
        "decisions_answered": len(made),
        "remaining_decision_ids": remaining,
        "complete": run.completed_at is not None,
        "score_so_far": clamp(raw_total(made)),
        "raw_score_so_far": round(raw_total(made), 1),
        "final_score": run.final_score,
        "decisions": [
            {"decision_id": d.decision_id, "choice": d.choice,
             "score_delta": d.score_delta, "justification": d.reasons}
            for d in made
        ],
    }


# ---------------------------------------------------------------- writing
def start(session: Session, template_id: str, locale: str, seed: int,
          learner_id: Optional[str] = None) -> ScenarioRun:
    run = ScenarioRun(learner_id=learner_id or None, template_id=template_id,
                      locale=locale.lower(), seed=seed)
    session.add(run); session.commit(); session.refresh(run)
    return run


def record_decision(session: Session, run: ScenarioRun, scenario: Dict[str, Any],
                    decision_id: str, choice: str) -> Dict[str, Any]:
    """Score one decision inside a run and return it with the cumulative
    total, which is the number a learner can trust."""
    if run.completed_at is not None:
        raise RunConflictError("this run is already complete")
    decision = next((d for d in scenario["decisions"] if d["id"] == decision_id), None)
    if decision is None:
        valid = sorted(d["id"] for d in scenario["decisions"])
        raise RunIncompleteError(f"decision_id must be one of {valid}")
    if choice not in decision["options"]:
        raise RunIncompleteError(f"choice '{choice}' is not an option for "
                                 f"'{decision_id}'. Options: {decision['options']}")
    made = decisions_of(session, run.id)
    if any(d.decision_id == decision_id for d in made):
        raise RunConflictError(f"'{decision_id}' has already been answered in this run")

    result = scoring.score_decision(scenario, decision_id, choice)
    row = RunDecision(run_id=run.id, decision_id=decision_id, choice=choice,
                      score_delta=result["score_delta"],
                      justification=json.dumps(result["justification"]))
    session.add(row); session.commit()

    made = decisions_of(session, run.id)
    answered = {d.decision_id for d in made}
    remaining = [d["id"] for d in scenario["decisions"] if d["id"] not in answered]
    return {
        "run_id": run.id,
        "decision_id": decision_id,
        "choice": choice,
        "score_delta": result["score_delta"],
        "justification": result["justification"],
        # The number on screen: every decision in this run so far, not just this one.
        "score_so_far": clamp(raw_total(made)),
        "raw_score_so_far": round(raw_total(made), 1),
        "decisions_answered": len(made),
        "decisions_total": len(scenario["decisions"]),
        "remaining_decision_ids": remaining,
        "complete": False,
    }


def complete(session: Session, run: ScenarioRun, scenario: Dict[str, Any]) -> Dict[str, Any]:
    """Finish a run. Refused until every decision has been answered, so a
    final score always means the whole scenario."""
    if run.completed_at is not None:
        raise RunConflictError("this run is already complete")
    made = decisions_of(session, run.id)
    answered = {d.decision_id for d in made}
    remaining = [d["id"] for d in scenario["decisions"] if d["id"] not in answered]
    if remaining:
        raise RunIncompleteError(
            f"{len(remaining)} decision(s) still unanswered: {remaining}")

    run.final_score = clamp(raw_total(made))
    run.completed_at = _now()
    session.add(run); session.commit(); session.refresh(run)

    worst = min(made, key=lambda d: d.score_delta, default=None)
    summary = state(session, run, scenario)
    summary["final_score"] = run.final_score
    summary["complete"] = True
    summary["biggest_mistake"] = (
        {"decision_id": worst.decision_id, "choice": worst.choice,
         "score_delta": worst.score_delta, "why": (worst.reasons or [""])[0]}
        if worst is not None and worst.score_delta < 0 else None
    )
    return summary
