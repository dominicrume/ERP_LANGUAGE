#!/usr/bin/env bash
# Apply pending schema migrations to the database in ERPSIM_DATABASE_URL
# (default: the local sqlite file). Safe to run twice.
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-.venv/bin/python}"
PYTHONPATH=src "$PY" - "$@" <<'PYEOF'
import logging, sys
logging.basicConfig(level=logging.INFO, format="%(message)s")
from erpsim import main, migrations
engine = main.make_engine(main.database_url())
before = migrations.current_version(engine)
applied = migrations.migrate(engine)
after = migrations.current_version(engine)
print(f"schema v{before} -> v{after}" + (f", applied {applied}" if applied else ", already up to date"))
PYEOF
