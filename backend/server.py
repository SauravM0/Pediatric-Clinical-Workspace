"""FastAPI backend for the Pediatric Clinical Workspace.

The service serves the static frontend from ``frontend/index.html`` so the
project can be run with one local command. It binds to ``127.0.0.1`` only and
performs no external network calls: no API keys, no cloud inference, nothing
leaves this computer.

The previous unvalidated whole-image bone-age heuristic has been removed from
the clinical path (cleanup §6.1). TW3-RUS bone age is produced only by the
deterministic scoring engine in ``backend/tw3/scoring.py`` from doctor-confirmed
bone stages. The structured assessment/upload API is being built in ``backend``.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.api_auth import router as auth_router
from backend.api_bone_age import router as bone_age_router
from backend.api_assessments import router as assessments_router
from backend.api_clinical import router as clinical_router
from backend.api_cvd import router as cvd_router
from backend.api_growth import router as growth_router
from backend.api_growth_report import router as growth_report_router
from backend.api_hepatic import router as hepatic_router
from backend.api_observations import router as observations_router
from backend.api_privacy import router as privacy_router
from backend.api_renal import router as renal_router
from backend.api_reference_data import router as reference_data_router
from backend.api_vitals import router as vitals_router
from backend.config import APP_VERSION
from backend.db import init_db

APP_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = APP_ROOT / "frontend"
INDEX_HTML = FRONTEND_DIR / "index.html"
ENV_FILE = APP_ROOT / ".env"


def _load_env_file(path: Path) -> None:
    """Load simple KEY=VALUE pairs without overriding real environment vars."""
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = value


_load_env_file(ENV_FILE)

app = FastAPI(title="Pediatric Clinical Workspace", version=APP_VERSION)

init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8077",
        "http://127.0.0.1:8077",
        "http://localhost:3131",
        "http://127.0.0.1:3131",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        # "null" was listed here, with credentials allowed. A sandboxed iframe on
        # ANY web site has origin "null", so that let an arbitrary page the
        # clinician visited read patient data from this local server. Removed.
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Outermost layer: host allowlist (DNS rebinding), loopback-only while auth is
# off, cross-site write refusal, security headers. See security/network_guard.py.
from backend.security.network_guard import NetworkGuardMiddleware  # noqa: E402

app.add_middleware(NetworkGuardMiddleware)


class _RevalidatingStatics(StaticFiles):
    """StaticFiles that always revalidates.

    Starlette sends ETag and Last-Modified but no Cache-Control. With no
    Cache-Control a browser applies HEURISTIC caching -- typically a fraction of
    the time since Last-Modified -- and may serve a stale file without asking.
    Measured here: after rebuilding frontend/app.js, a fresh tab still executed
    the previous 293,561-byte bundle while a no-store fetch of the same URL
    returned the new 295,729-byte one.

    That is a deployment problem, not just a development annoyance. app.js is
    referenced from index.html with no version in the URL, so a clinical fix
    could ship and clinicians keep running the code it replaced, with nothing to
    indicate it.

    ``no-cache`` means "revalidate before use", NOT "do not store": the browser
    still keeps the file and still gets a 304 when nothing changed, so the
    offline-first property is unaffected.
    """

    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers.setdefault("Cache-Control", "no-cache")
        return response


if FRONTEND_DIR.exists():
    app.mount("/static", _RevalidatingStatics(directory=FRONTEND_DIR), name="static")
    vendor_dir = FRONTEND_DIR / "vendor"
    if vendor_dir.exists():
        # Locally vendored JS (React, ReactDOM) referenced as ``vendor/*`` from
        # index.html — served here so the app is fully offline. These are
        # version-pinned files that do not change, but they get the same
        # revalidation so a vendor upgrade cannot be missed either.
        app.mount("/vendor", _RevalidatingStatics(directory=vendor_dir), name="vendor")


def _warm_growth_cache() -> None:
    """Build the chart series the browser asks for first, in the background.

    A cold series build takes ~2-3 s, and the first requests after a restart
    queued behind it: eGFR, BP and QRISK3 results showed "Calculating..." for
    about 2.5 s. Warming the exact (measure, sex, defaults) the frontend requests
    removes that. A daemon thread, so startup is not delayed and shutdown is not
    blocked; a failure here only means the first request builds it instead.
    """
    import logging
    try:
        from backend.api_growth import _series
        for sex in ("girls", "boys"):
            for measure in ("height", "weight", "bmi"):
                _series(measure, sex, 0.0, 18.0, 0.1)
    except Exception:  # noqa: BLE001 -- best-effort optimisation only
        logging.getLogger(__name__).warning("growth cache warm-up failed", exc_info=True)


if os.environ.get("PCW_SKIP_CACHE_WARMUP") != "1":
    import threading
    threading.Thread(target=_warm_growth_cache, name="growth-cache-warmup", daemon=True).start()


app.include_router(auth_router)
app.include_router(bone_age_router)
app.include_router(assessments_router)
app.include_router(clinical_router)
app.include_router(cvd_router)
app.include_router(growth_router)
app.include_router(growth_report_router)
app.include_router(observations_router)
app.include_router(privacy_router)
app.include_router(renal_router)
app.include_router(hepatic_router)
app.include_router(vitals_router)
app.include_router(reference_data_router)


@app.get("/api/health")
def health() -> dict[str, Any]:
    """Unauthenticated on purpose: a liveness probe must work before login, and
    this returns no patient data. It DOES disclose the security posture --
    an instance running with auth or encryption off should be visibly so, not
    quietly so (security phase, C.1/C.2)."""
    from backend.security.crypto import encryption_available, key_location
    from backend.security.deps import auth_disabled

    auth_on = not auth_disabled()
    encryption_on = encryption_available()
    key_loc = key_location() if encryption_on else {"source": "none", "inside_app_folder": False}
    return {
        "status": "ok",
        "frontend_available": INDEX_HTML.exists(),
        "external_calls": False,
        "clinical_use": False,
        "auth_enabled": auth_on,
        "encryption_at_rest": encryption_on,
        "encryption_key_source": key_loc["source"],
        "safe_for_patient_data": auth_on and encryption_on,
        "warnings": [
            w for w in (
                None if auth_on else
                "AUTHENTICATION IS OFF - every endpoint is open to anyone who can reach "
                "this app, and approvals are attributed to 'dev-no-auth' rather than to a "
                "named clinician. This is the shipped default (there is no sign-in screen); "
                "set PCW_AUTH_ENABLED=1 to restore enforcement. Never expose this instance "
                "to a network.",
                None if encryption_on else
                "IDENTIFIERS NOT ENCRYPTED AT REST (PCW_ENCRYPTION_KEY unset) - patient "
                "names are stored in clear in the database file.",
                None if not key_loc["inside_app_folder"] else
                "ENCRYPTION KEY IS INSIDE THE APP FOLDER - a copy of the folder carries the "
                "database and the key that unlocks it. Move the key to a file elsewhere and "
                "point PCW_ENCRYPTION_KEY_FILE at it.",
            ) if w
        ],
    }


@app.get("/")
def index() -> Any:
    if not INDEX_HTML.exists():
        return JSONResponse(
            status_code=404,
            content={"error": "frontend_missing", "detail": str(INDEX_HTML)},
        )
    # Must revalidate. index.html carries the versioned bundle URL
    # (static/app.js?v=<hash>, stamped by build.mjs), so a cached copy of THIS
    # file pins the browser to whichever bundle it named when it was cached --
    # the version query cannot help if the page announcing it is itself stale.
    return FileResponse(INDEX_HTML, headers={"Cache-Control": "no-cache"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", "8077")))
