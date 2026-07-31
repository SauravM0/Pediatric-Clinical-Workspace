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
from backend.api_cvd import router as cvd_router
from backend.api_growth import router as growth_router
from backend.api_growth_report import router as growth_report_router
from backend.api_observations import router as observations_router
from backend.api_privacy import router as privacy_router
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
        "null",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
    vendor_dir = FRONTEND_DIR / "vendor"
    if vendor_dir.exists():
        # Locally vendored JS (React, Babel, Tailwind) referenced as ``vendor/*``
        # from index.html — served here so the app is fully offline.
        app.mount("/vendor", StaticFiles(directory=vendor_dir), name="vendor")


app.include_router(auth_router)
app.include_router(bone_age_router)
app.include_router(assessments_router)
app.include_router(cvd_router)
app.include_router(growth_router)
app.include_router(growth_report_router)
app.include_router(observations_router)
app.include_router(privacy_router)


@app.get("/api/health")
def health() -> dict[str, Any]:
    """Unauthenticated on purpose: a liveness probe must work before login, and
    this returns no patient data. It DOES disclose the security posture --
    an instance running with auth or encryption off should be visibly so, not
    quietly so (security phase, C.1/C.2)."""
    from backend.security.crypto import encryption_available
    from backend.security.deps import auth_disabled

    auth_on = not auth_disabled()
    encryption_on = encryption_available()
    return {
        "status": "ok",
        "frontend_available": INDEX_HTML.exists(),
        "external_calls": False,
        "clinical_use": False,
        "auth_enabled": auth_on,
        "encryption_at_rest": encryption_on,
        "safe_for_patient_data": auth_on and encryption_on,
        "warnings": [
            w for w in (
                None if auth_on else
                "AUTHENTICATION DISABLED (PCW_AUTH_DISABLED) - every endpoint is open. "
                "Development only; never expose this instance or store real patient data.",
                None if encryption_on else
                "IDENTIFIERS NOT ENCRYPTED AT REST (PCW_ENCRYPTION_KEY unset) - patient "
                "names are stored in clear in the database file.",
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
    return FileResponse(INDEX_HTML)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", "8077")))
