#!/usr/bin/env bash
# The ship gate: tests, then the ROOTS soil check. Non-zero on either failure.
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-.venv/bin/python}"
"$PY" -m pytest -q
"$PY" rules/roots/check_roots.py .
