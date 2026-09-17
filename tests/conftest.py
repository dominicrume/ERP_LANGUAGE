"""Shared fixtures. The API client uses an isolated in-memory DB so tests
never touch the erpsim.db of whoever is running them."""
import os

# Importing the app builds its engine. Point it at memory BEFORE the import
# so a test run never creates or touches ./erpsim.db in the working dir.
os.environ.setdefault("ERPSIM_DATABASE_URL", "sqlite://")
# The write limiter protects a running demo from one noisy client. A test run
# is one client making thousands of writes on purpose, so it is off here and
# exercised directly in tests/test_web_hardening.py.
os.environ.setdefault("ERPSIM_WRITE_LIMIT_PER_MINUTE", "0")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import create_engine

from erpsim import main, migrations


@pytest.fixture
def client(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    migrations.migrate(engine)
    monkeypatch.setattr(main, "engine", engine)
    with TestClient(main.app) as c:
        yield c
