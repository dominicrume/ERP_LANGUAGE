"""What the API needs in front of it before anyone but the author runs it.

None of this changes a score. It is the layer that decides how the service
behaves when it is reached by something other than a well-behaved browser:
oversized bodies, floods of writes, a crash, or a page embedded in someone
else's site.

Deliberately dependency-free. Each piece is a few lines of Starlette
middleware, and swapping any of them for a real gateway (nginx, Cloudflare,
an API gateway) is the expected path once this is hosted.
"""
from __future__ import annotations

import logging
import os
import time
import uuid
from collections import deque
from threading import Lock
from typing import Deque, Dict, Tuple

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

log = logging.getLogger("erpsim.web")

# The page loads fonts and icons from two CDNs. Everything else is same-origin.
FONT_HOSTS = "https://fonts.googleapis.com https://cdn.jsdelivr.net"
FONT_FILE_HOSTS = "https://fonts.gstatic.com https://cdn.jsdelivr.net"
CSP = (
    "default-src 'self'; "
    f"style-src 'self' 'unsafe-inline' {FONT_HOSTS}; "
    f"font-src 'self' {FONT_FILE_HOSTS}; "
    "img-src 'self' data:; "
    "script-src 'self' 'unsafe-inline'; "
    "connect-src 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "object-src 'none'"
)
SECURITY_HEADERS = {
    "Content-Security-Policy": CSP,
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), interest-cohort=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}

MAX_BODY_BYTES = int(os.environ.get("ERPSIM_MAX_BODY_BYTES", 256 * 1024))
WRITE_LIMIT_PER_MINUTE = int(os.environ.get("ERPSIM_WRITE_LIMIT_PER_MINUTE", 120))


def _env_flag(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Defence in depth for a page that renders instructor-authored text.
    The escaping in the frontend is the real fix; this is the second lock."""

    def __init__(self, app, https_only: bool = False):
        super().__init__(app)
        self.https_only = https_only

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        for header, value in SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        if self.https_only:
            response.headers.setdefault("Strict-Transport-Security",
                                        "max-age=31536000; includeSubDomains")
        return response


class RequestIdMiddleware(BaseHTTPMiddleware):
    """One id per request, in the log line and in the response, so a learner
    reporting "it broke" can be matched to what the server saw."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        request.state.request_id = request_id
        started = time.perf_counter()
        response = await call_next(request)
        took_ms = (time.perf_counter() - started) * 1000
        response.headers["X-Request-Id"] = request_id
        log.info("%s %s %s %.1fms id=%s", request.method, request.url.path,
                 response.status_code, took_ms, request_id)
        return response


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """An authored scenario is a few kilobytes. Anything far larger is either
    a mistake or an attempt to fill the disk, and is refused before parsing."""

    def __init__(self, app, max_bytes: int = MAX_BODY_BYTES):
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next):
        declared = request.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > self.max_bytes:
            return JSONResponse(
                {"detail": f"request body is larger than {self.max_bytes} bytes"}, status_code=413)
        return await call_next(request)


class WriteRateLimitMiddleware(BaseHTTPMiddleware):
    """A crude per-client ceiling on writes, so one script cannot fill the
    runs table or the template folder. In-process on purpose: it protects a
    single-process demo, and a real deployment puts this at the edge."""

    def __init__(self, app, per_minute: int = WRITE_LIMIT_PER_MINUTE):
        super().__init__(app)
        self.per_minute = per_minute
        self._hits: Dict[str, Deque[float]] = {}
        self._lock = Lock()

    def _allow(self, client: str, now: float) -> Tuple[bool, int]:
        with self._lock:
            hits = self._hits.setdefault(client, deque())
            while hits and now - hits[0] > 60.0:
                hits.popleft()
            if len(hits) >= self.per_minute:
                return False, int(60 - (now - hits[0])) + 1
            hits.append(now)
            if len(self._hits) > 4096:                       # pragma: no cover - housekeeping
                for key in [k for k, v in self._hits.items() if not v][:1024]:
                    self._hits.pop(key, None)
            return True, 0

    async def dispatch(self, request: Request, call_next):
        if request.method in {"GET", "HEAD", "OPTIONS"} or self.per_minute <= 0:
            return await call_next(request)
        client = request.client.host if request.client else "unknown"
        allowed, retry_after = self._allow(client, time.monotonic())
        if not allowed:
            log.warning("rate limited %s on %s", client, request.url.path)
            return JSONResponse(
                {"detail": "too many writes from this address, slow down"},
                status_code=429, headers={"Retry-After": str(retry_after)})
        return await call_next(request)


def install(app: FastAPI) -> None:
    """Wire the layer up. Order matters: the id is outermost so even a
    refused request is logged with one."""
    app.add_middleware(WriteRateLimitMiddleware)
    app.add_middleware(BodySizeLimitMiddleware)
    app.add_middleware(SecurityHeadersMiddleware,
                       https_only=_env_flag("ERPSIM_HTTPS_ONLY", False))
    app.add_middleware(RequestIdMiddleware)

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):        # pragma: no cover - last resort
        """A crash gives the learner an id to quote, never a stack trace."""
        request_id = getattr(request.state, "request_id", "unknown")
        log.exception("unhandled error id=%s path=%s", request_id, request.url.path)
        return JSONResponse(
            {"detail": "Something went wrong on the server. Nothing was saved.",
             "request_id": request_id}, status_code=500)
