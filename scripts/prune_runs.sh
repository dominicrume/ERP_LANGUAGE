#!/usr/bin/env bash
# Remove sittings that were started and never finished, older than N days
# (default 30). Completed runs are never touched: they are a learner's
# history. Safe to run repeatedly; prints what it would do with --dry-run.
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-.venv/bin/python}"
PYTHONPATH=src "$PY" - "$@" <<'PYEOF'
import sys, logging
from datetime import datetime, timedelta, timezone
from sqlmodel import Session, select, delete
logging.basicConfig(level=logging.INFO, format="%(message)s")
from erpsim import main
from erpsim.runs import ScenarioRun, RunDecision

args = [a for a in sys.argv[1:] if a != "--dry-run"]
dry = "--dry-run" in sys.argv[1:]
days = int(args[0]) if args else 30
cutoff = datetime.now(timezone.utc) - timedelta(days=days)

with Session(main.engine) as s:
    stale = list(s.exec(select(ScenarioRun).where(
        ScenarioRun.completed_at.is_(None), ScenarioRun.started_at < cutoff)))
    print(f"{len(stale)} unfinished sitting(s) started before {cutoff.date()}"
          + (" (dry run, nothing removed)" if dry else ""))
    if stale and not dry:
        ids = [r.id for r in stale]
        s.exec(delete(RunDecision).where(RunDecision.run_id.in_(ids)))
        s.exec(delete(ScenarioRun).where(ScenarioRun.id.in_(ids)))
        s.commit()
        print(f"removed {len(ids)}; completed sittings were not touched")
PYEOF
