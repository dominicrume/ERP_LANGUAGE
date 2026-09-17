"""Shared fixtures. The API client uses an isolated in-memory DB so tests
never touch the erpsim.db of whoever is running them."""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine
from sqlalchemy.pool import StaticPool

from erpsim import main


@pytest.fixture
def client(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(main, "engine", engine)
    with TestClient(main.app) as c:
        yield c
