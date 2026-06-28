"""FastAPI backend for the Pediatric Clinical Workspace.

The service exposes a local bone-age API and serves the static frontend from
``frontend/index.html`` so the project can be run with one command.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.local_bone_age import (
    make_synthetic_hand_xray,
    model_status,
    predict_bone_age,
)

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

app = FastAPI(title="Pediatric Clinical Workspace", version="1.1.0")

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
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/api/health")
def health() -> dict[str, Any]:
    status = model_status()
    return {
        "status": "ok",
        "inference": status,
        "model": status["kind"],
        "model_configured": status["configured"],
        "frontend_available": INDEX_HTML.exists(),
        "clinical_use": False,
    }


@app.post("/api/bone-age")
async def bone_age(
    file: UploadFile = File(...),
    sex: str = Form("unspecified"),
    chronological_age: str = Form(""),
) -> Any:
    try:
        raw = await file.read()
        if not raw:
            return JSONResponse(status_code=400, content={"error": "empty_file"})
        return predict_bone_age(raw, sex, chronological_age)
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"error": "inference_failed", "detail": str(exc)},
        )


@app.get("/api/self-test")
def self_test() -> Any:
    try:
        raw = make_synthetic_hand_xray()
        result = predict_bone_age(raw, sex="boys", chronological_age="10.0")
        return {
            "status": "pass",
            "message": "Local upload and prediction path is working.",
            "result": result,
        }
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={
                "status": "fail",
                "error": "self_test_failed",
                "detail": str(exc),
            },
        )


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
