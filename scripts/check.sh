#!/usr/bin/env bash
# The ship gate: migrations apply cleanly, tests pass, then the ROOTS soil
# check. Non-zero on any failure.
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-.venv/bin/python}"

# Migrations must run from nothing to latest on a throwaway database, twice.
TMPDB="$(mktemp -t erpsim-gate-XXXXXX).db"
trap 'rm -f "$TMPDB"' EXIT
# Importing the app migrates its own database, so the gate builds its engine
# directly: this must prove the migrations run, not that startup ran them.
PYTHONPATH=src TMPDB="$TMPDB" "$PY" - <<'PYEOF'
import os
from sqlmodel import create_engine
from erpsim import migrations
engine = create_engine(f"sqlite:///{os.environ['TMPDB']}")
applied = migrations.migrate(engine)
assert applied == [m[0] for m in migrations.MIGRATIONS], applied
assert migrations.migrate(engine) == [], "migrations are not idempotent"
print(f"migrations: v0 -> v{migrations.LATEST}, idempotent")
PYEOF

"$PY" -m pytest -q
"$PY" rules/roots/check_roots.py .
