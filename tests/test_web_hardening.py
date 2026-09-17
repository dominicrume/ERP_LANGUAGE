"""The layer in front of the API: headers, limits, logging, health.

None of it changes a score. All of it decides how the service behaves when
something other than a well-behaved browser reaches it.
"""
import importlib
import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from erpsim import web


# ---------------------------------------------------------------- headers
def test_every_response_carries_the_security_headers(client):
    r = client.get("/")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["Referrer-Policy"] == "no-referrer"
    assert "frame-ancestors 'none'" in r.headers["Content-Security-Policy"]


def test_the_content_policy_allows_exactly_what_the_page_loads():
    """The page pulls fonts and icons from two CDNs and nothing else. A
    policy that forgets one breaks the page; one that allows everything is
    not a policy."""
    csp = web.CSP
    assert "https://fonts.googleapis.com" in csp and "https://cdn.jsdelivr.net" in csp
    assert "connect-src 'self'" in csp          # the API is same-origin
    assert "object-src 'none'" in csp
    for forbidden in ("*", "unsafe-eval"):
        assert f" {forbidden};" not in csp


def test_https_is_only_asserted_when_the_deployment_says_so(client):
    """Sending HSTS from a local http demo would poison the browser."""
    assert "Strict-Transport-Security" not in client.get("/").headers


# ---------------------------------------------------------------- request ids
def test_a_request_id_comes_back_and_a_client_supplied_one_is_kept(client):
    assert len(client.get("/health").headers["X-Request-Id"]) >= 8
    r = client.get("/health", headers={"X-Request-Id": "trace-me-123"})
    assert r.headers["X-Request-Id"] == "trace-me-123"


# ---------------------------------------------------------------- body size
def test_an_oversized_body_is_refused_before_it_is_parsed(client):
    payload = {"title": "x" * (300 * 1024), "industry": "y"}
    r = client.post("/instructor/drafts/preview", json=payload)
    assert r.status_code == 413
    assert "larger than" in r.json()["detail"]


def test_an_ordinary_draft_is_nowhere_near_the_limit(client):
    draft = {"title": "Fine", "industry": "y", "narrative": "about {{product}}",
             "product_pool": ["a"],
             "decisions": [{"label": "q", "options": [
                 {"label": "a", "impacts": [{"kpi": "m", "points": 1}], "reason": "r {delta}"},
                 {"label": "b", "impacts": [{"kpi": "m", "points": 2}], "reason": "r {delta}"}]}],
             "kpi_weights": {"m": 100}}
    assert client.post("/instructor/drafts/preview", json=draft).status_code == 200


# ---------------------------------------------------------------- rate limit
@pytest.fixture
def limited_app():
    app = FastAPI()
    app.add_middleware(web.WriteRateLimitMiddleware, per_minute=3)

    @app.post("/write")
    def write():
        return {"ok": True}

    @app.get("/read")
    def read():
        return {"ok": True}

    return TestClient(app)


def test_a_flood_of_writes_is_slowed_down(limited_app):
    codes = [limited_app.post("/write").status_code for _ in range(5)]
    assert codes == [200, 200, 200, 429, 429]
    assert limited_app.post("/write").headers["Retry-After"].isdigit()


def test_reading_is_never_rate_limited(limited_app):
    for _ in range(5):
        limited_app.post("/write")
    assert all(limited_app.get("/read").status_code == 200 for _ in range(10))


def test_the_limiter_can_be_switched_off_for_a_trusted_deployment():
    app = FastAPI()
    app.add_middleware(web.WriteRateLimitMiddleware, per_minute=0)

    @app.post("/write")
    def write():
        return {"ok": True}

    c = TestClient(app)
    assert all(c.post("/write").status_code == 200 for _ in range(20))


# ---------------------------------------------------------------- health
def test_health_reports_what_it_actually_checked(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["checks"] == {"database": "ok", "schema": "ok", "content": "ok"}
    assert body["version"] and body["scenarios"] == body["templates"] * body["locales"]


def test_health_turns_red_when_the_database_is_gone(client, monkeypatch):
    """A health check that cannot fail is decoration."""
    from erpsim import main
    monkeypatch.setattr(main, "engine", main.make_engine("sqlite:////nonexistent/path/db.sqlite"))
    r = client.get("/health")
    assert r.status_code == 503
    assert r.json()["status"] == "degraded"
    assert r.json()["checks"]["database"].startswith("unreachable")


# ---------------------------------------------------------------- deployment switches
@pytest.mark.parametrize("value,expected", [("1", True), ("true", True), ("on", True),
                                            ("0", False), ("false", False), ("no", False)])
def test_deployment_flags_read_the_environment(value, expected, monkeypatch):
    monkeypatch.setenv("ERPSIM_TEST_FLAG", value)
    assert web._env_flag("ERPSIM_TEST_FLAG", not expected) is expected


def test_interactive_docs_can_be_closed_in_production(monkeypatch):
    monkeypatch.setenv("ERPSIM_PUBLIC_DOCS", "false")
    monkeypatch.setenv("ERPSIM_DATABASE_URL", "sqlite://")
    import erpsim.main as main
    reloaded = importlib.reload(main)
    try:
        assert reloaded.app.docs_url is None and reloaded.app.redoc_url is None
    finally:
        monkeypatch.setenv("ERPSIM_PUBLIC_DOCS", "true")
        importlib.reload(main)
