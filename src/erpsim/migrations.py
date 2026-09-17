"""Schema versioning.

`SQLModel.metadata.create_all()` creates missing tables and nothing else:
it never adds a column to a table that already exists. Until this module,
the next schema change would have silently ignored or corrupted the learner
data already in someone's database (CONTEXT.md gap F).

Each migration is numbered, applied in order, and recorded in a
`schema_version` table. Running twice is a no-op. Running an older build
against a newer database refuses rather than guesses.

Deliberately not Alembic: the project ships with five runtime dependencies
and this is a few hundred lines of ordered SQL. If migrations ever need
branching or autogeneration, swap this for Alembic and keep the version
table's meaning.
"""
from __future__ import annotations

import logging
from typing import Callable, List, Tuple

from sqlalchemy import inspect, text
from sqlmodel import SQLModel

log = logging.getLogger("erpsim.migrations")

# Importing the models registers them on SQLModel.metadata.
from . import memory, runs  # noqa: E402,F401

LEARNER_KEY = ("learner_id", "template_id", "locale")
UNIQUE_INDEX = "ix_learnerprogress_learner_template_locale"


def _columns(conn, table: str) -> set:
    insp = inspect(conn)
    if table not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns(table)}


def _tables(conn) -> set:
    return set(inspect(conn).get_table_names())


# ---------------------------------------------------------------- migrations
def _m1_baseline(conn) -> None:
    """Every table the current models declare. On a database that predates
    versioning this only adds what is missing and leaves existing rows."""
    SQLModel.metadata.create_all(conn)


def _m2_runs_and_streaks(conn) -> None:
    """v1.0: a learner record counts completed runs and streaks."""
    existing = _columns(conn, "learnerprogress")
    additions = [
        ("runs_completed", "INTEGER NOT NULL DEFAULT 0"),
        ("best_run_score", "FLOAT"),
        ("current_streak", "INTEGER NOT NULL DEFAULT 0"),
        ("longest_streak", "INTEGER NOT NULL DEFAULT 0"),
        ("last_completed_on", "DATE"),
    ]
    for name, ddl in additions:
        if name not in existing:
            conn.execute(text(f"ALTER TABLE learnerprogress ADD COLUMN {name} {ddl}"))
            log.info("added learnerprogress.%s", name)
    # Pre-v1.0 rows counted decisions, not sittings. Claiming those were runs
    # would be a lie, so they start at zero (see CHANGELOG).


def _m3_one_row_per_learner_template_locale(conn) -> None:
    """Fold any duplicate learner rows together, then make duplicates
    impossible. Without the constraint, two interleaved writes could each
    insert a row and every later read would see only the first
    (CONTEXT.md gap G)."""
    if "learnerprogress" not in _tables(conn):
        return
    dupes = conn.execute(text(
        "SELECT learner_id, template_id, locale FROM learnerprogress "
        "GROUP BY learner_id, template_id, locale HAVING COUNT(*) > 1")).fetchall()
    for learner_id, template_id, locale in dupes:
        rows = conn.execute(text(
            "SELECT id, attempts, best_score, runs_completed, best_run_score, current_streak, "
            "longest_streak, last_completed_on, last_mistake FROM learnerprogress "
            "WHERE learner_id=:l AND template_id=:t AND locale=:c ORDER BY id"),
            {"l": learner_id, "t": template_id, "c": locale}).fetchall()
        keep = rows[0]
        merged = {
            "attempts": sum(r[1] or 0 for r in rows),
            "best_score": max((r[2] or 0.0) for r in rows),
            "runs_completed": sum(r[3] or 0 for r in rows),
            "best_run_score": max([r[4] for r in rows if r[4] is not None], default=None),
            "current_streak": max((r[5] or 0) for r in rows),
            "longest_streak": max((r[6] or 0) for r in rows),
            "last_completed_on": max([r[7] for r in rows if r[7] is not None], default=None),
            "last_mistake": next((r[8] for r in reversed(rows) if r[8]), None),
        }
        conn.execute(text(
            "UPDATE learnerprogress SET attempts=:attempts, best_score=:best_score, "
            "runs_completed=:runs_completed, best_run_score=:best_run_score, "
            "current_streak=:current_streak, longest_streak=:longest_streak, "
            "last_completed_on=:last_completed_on, last_mistake=:last_mistake WHERE id=:id"),
            {**merged, "id": keep[0]})
        conn.execute(text("DELETE FROM learnerprogress WHERE learner_id=:l AND template_id=:t "
                          "AND locale=:c AND id != :id"),
                     {"l": learner_id, "t": template_id, "c": locale, "id": keep[0]})
        log.warning("merged %d duplicate rows for %s/%s/%s", len(rows), learner_id, template_id, locale)
    conn.execute(text(f"CREATE UNIQUE INDEX IF NOT EXISTS {UNIQUE_INDEX} "
                      f"ON learnerprogress ({', '.join(LEARNER_KEY)})"))


MIGRATIONS: List[Tuple[int, str, Callable]] = [
    (1, "baseline: every table the models declare", _m1_baseline),
    (2, "v1.0: completed runs and streaks on the learner record", _m2_runs_and_streaks),
    (3, "one row per learner, template and locale", _m3_one_row_per_learner_template_locale),
]
LATEST = MIGRATIONS[-1][0]


# ---------------------------------------------------------------- runner
class SchemaTooNewError(RuntimeError):
    """The database was written by a newer build than this one."""


def _ensure_version_table(conn) -> None:
    conn.execute(text("CREATE TABLE IF NOT EXISTS schema_version ("
                      "version INTEGER NOT NULL, applied_at TIMESTAMP)"))


def current_version(engine) -> int:
    with engine.begin() as conn:
        _ensure_version_table(conn)
        row = conn.execute(text("SELECT MAX(version) FROM schema_version")).scalar()
        return int(row or 0)


def migrate(engine) -> List[int]:
    """Apply every pending migration in order. Idempotent. Returns the
    versions applied, so a caller can log or assert on them."""
    applied = []
    with engine.begin() as conn:
        _ensure_version_table(conn)
        version = int(conn.execute(text("SELECT MAX(version) FROM schema_version")).scalar() or 0)
        if version > LATEST:
            raise SchemaTooNewError(
                f"database is at schema v{version}, this build only knows v{LATEST}. "
                f"Upgrade the application rather than downgrading the database.")
        for number, description, fn in MIGRATIONS:
            if number <= version:
                continue
            log.info("applying migration %d: %s", number, description)
            fn(conn)
            conn.execute(text("INSERT INTO schema_version (version, applied_at) "
                              "VALUES (:v, CURRENT_TIMESTAMP)"), {"v": number})
            applied.append(number)
    return applied
