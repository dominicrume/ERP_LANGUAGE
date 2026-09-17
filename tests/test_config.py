"""ENGINEERING.md #5 / SCALING.md #1: the database DSN is runtime config."""
from erpsim import main


def test_default_dsn_is_sqlite_dev(monkeypatch):
    monkeypatch.delenv("ERPSIM_DATABASE_URL", raising=False)
    assert main.database_url() == "sqlite:///erpsim.db"


def test_import_never_creates_a_db_file_in_cwd():
    """conftest points ERPSIM_DATABASE_URL at memory before import; the
    engine the app built must not be a file in the working directory."""
    assert str(main.engine.url) == "sqlite://"


def test_dsn_comes_from_environment(monkeypatch, tmp_path):
    url = f"sqlite:///{tmp_path}/other.db"
    monkeypatch.setenv("ERPSIM_DATABASE_URL", url)
    assert main.database_url() == url
    eng = main.make_engine(main.database_url())
    assert str(eng.url) == url


def test_non_sqlite_dsn_gets_no_sqlite_connect_args():
    """No driver needed: only the kwargs decision is under test."""
    assert main.engine_kwargs("postgresql+psycopg2://u:p@localhost/erpsim") == {}
    assert main.engine_kwargs("sqlite:///x.db") == {"connect_args": {"check_same_thread": False}}
