"""Central version and path configuration (directive §7, §24).

Versions are recorded on every approved assessment so old results stay
reproducible. The database lives locally under ``backend/data`` (gitignored;
never commit PHI).
"""

from __future__ import annotations

import os
from pathlib import Path

APP_VERSION = "1.5.0"
# 4: security phase -- app_user, user_session, consent_record,
#    erasure_request, security_event; Patient.name encrypted at rest.
DB_SCHEMA_VERSION = "4"
REPORT_TEMPLATE_VERSION = "1.0"

APP_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = APP_ROOT / "backend" / "data"
RADIOGRAPH_DIR = DATA_DIR / "radiographs"

# Allow override (e.g. tests use an in-memory or temp DB).
DB_PATH = Path(os.environ.get("TW3_DB_PATH", str(DATA_DIR / "tw3.db")))


def database_url() -> str:
    return f"sqlite:///{DB_PATH.as_posix()}"
