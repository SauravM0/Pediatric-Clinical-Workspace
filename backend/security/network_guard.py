"""Network-facing protections for a local clinical app (step 6).

Authentication is OFF by default in this product (a deliberate owner decision;
see deps.auth_disabled). That makes the network boundary the security boundary,
and several things that looked harmless behind a login stop being harmless:

1. **DNS rebinding.** A web page the clinician happens to visit can point its own
   domain at 127.0.0.1 and then talk to this app as same-origin, reading every
   patient record. Browsers send the attacker's domain in the Host header, so
   accepting only known hosts defeats it (``allowed_hosts``).
2. **Remote clients with no login.** ``python -m backend.server`` binds to
   127.0.0.1, but any other launch (``uvicorn --host 0.0.0.0``, the old
   Procfile/render.yaml) exposes every record to the network. With auth off we
   refuse any client that is not this machine, whatever the bind address.
3. **Cross-site writes (CSRF).** Multipart upload endpoints accept a plain HTML
   form post, which any web page can send without a CORS preflight. State-changing
   requests from a foreign Origin, or that the browser labels cross-site, are
   refused.
4. **Browser hardening.** CSP (no third-party script, no framing), nosniff, no
   referrer, and ``Cache-Control: no-store`` on API responses so patient data is
   not left in the browser's disk cache.

Configuration (environment):
  PCW_ALLOWED_HOSTS   extra Host names, comma-separated (e.g. a clinic LAN name).
                      Only meaningful with authentication ON.
  PCW_LOCAL_CLIENTS   client addresses treated as "this machine" (default
                      loopback only). The test suite adds its fake client here.
"""
from __future__ import annotations

import ipaddress
import os
from typing import Iterable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

_LOOPBACK_NAMES = ("localhost", "127.0.0.1", "::1", "[::1]")
_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

CSP = ("default-src 'self'; script-src 'self'; "
       # index.html carries an inline <style> block (Tailwind itself is now a
       # static stylesheet built by build.mjs): 'unsafe-inline' for STYLES only.
       "style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; "
       "connect-src 'self'; font-src 'self' data:; object-src 'none'; "
       "base-uri 'self'; form-action 'self'; frame-ancestors 'none'")


def _csv_env(name: str) -> list[str]:
    return [x.strip().lower() for x in os.environ.get(name, "").split(",") if x.strip()]

def remote_clients_allowed() -> bool:
    return os.environ.get("PCW_ALLOW_REMOTE_CLIENTS", "").strip().lower() in ("1", "true", "yes")

def allowed_hosts() -> set[str]:
    return set(_LOOPBACK_NAMES) | set(_csv_env("PCW_ALLOWED_HOSTS"))


def _host_name(host_header: str) -> str:
    h = (host_header or "").strip().lower()
    if h.startswith("["):                       # [::1]:8077
        return h[: h.index("]") + 1] if "]" in h else h
    return h.rsplit(":", 1)[0] if h.count(":") == 1 else h


def is_local_client(host: str | None) -> bool:
    if not host:
        return False
    if host.lower() in _csv_env("PCW_LOCAL_CLIENTS"):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return host.lower() == "localhost"


def _origin_allowed(origin: str, hosts: Iterable[str]) -> bool:
    # "null" is what a sandboxed iframe or a file:// page sends -- i.e. any web
    # page that wants to hide where it came from. Never trusted.
    if origin == "null":
        return False
    try:
        from urllib.parse import urlsplit
        parts = urlsplit(origin)
    except ValueError:
        return False
    name = (parts.hostname or "").lower()
    if ":" in name:
        name = f"[{name}]"
    return parts.scheme in ("http", "https") and (name in hosts or name.strip("[]") in hosts)


class NetworkGuardMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        from backend.security.deps import auth_disabled

        hosts = allowed_hosts()
        is_probe = request.url.path == "/api/health" and request.method in ("GET", "HEAD")
        if not is_probe and _host_name(request.headers.get("host", "")) not in hosts:
            return JSONResponse({"detail": "host not allowed"}, status_code=400)

        client = request.client.host if request.client else None
        if auth_disabled() and not is_probe and not remote_clients_allowed() and not is_local_client(client):
            return JSONResponse(
                {"detail": "authentication is off, so this workspace only answers requests "
                           "from this computer. Enable PCW_AUTH_ENABLED to serve a network."},
                status_code=403)

        if request.method not in _SAFE_METHODS:
            origin = request.headers.get("origin")
            if origin is not None and not _origin_allowed(origin, hosts):
                return JSONResponse({"detail": "cross-site request refused"}, status_code=403)
            if request.headers.get("sec-fetch-site") == "cross-site":
                return JSONResponse({"detail": "cross-site request refused"}, status_code=403)

        response: Response = await call_next(request)
        h = response.headers
        h.setdefault("X-Content-Type-Options", "nosniff")
        h.setdefault("Referrer-Policy", "no-referrer")
        h.setdefault("X-Frame-Options", "DENY")
        h.setdefault("Content-Security-Policy", CSP)
        if request.url.path.startswith("/api/"):
            # Patient data must not be kept in the browser's disk cache.
            h["Cache-Control"] = "no-store"
        return response
