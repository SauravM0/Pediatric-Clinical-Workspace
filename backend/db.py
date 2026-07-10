"""Database engine, session and initialisation (directive §7, §23).

Local SQLite via SQLAlchemy. Foreign keys are enforced (off by default in
SQLite). ``init_db`` creates the schema and records the schema version.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from backend.config import DATA_DIR, DB_PATH, RADIOGRAPH_DIR, database_url

_connect_args = {"check_same_thread": False}
engine = create_engine(database_url(), connect_args=_connect_args, future=True)


@event.listens_for(engine, "connect")
def _enable_sqlite_fk(dbapi_connection, _record) -> None:  # pragma: no cover - driver hook
    cur = dbapi_connection.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


# Additive columns introduced after the first schema (schema v2). SQLite has no
# ALTER-heavy migration tooling here, so init_db backfills any that are missing
# on an existing local DB. All are nullable/defaulted → safe on populated tables.
_ADDED_COLUMNS: dict[str, dict[str, str]] = {
    "tw3_assessment": {
        "stage_system": "VARCHAR(24) NOT NULL DEFAULT 'tw3c-rus'",
        "total_carpal_score": "FLOAT",
        "carpal_bone_age_months": "INTEGER",
    },
    "bone_assessment": {"bone_group": "VARCHAR(8) NOT NULL DEFAULT 'rus'"},
    "radiograph": {"source_domain": "VARCHAR(24)"},
}


def _ensure_added_columns() -> None:
    """Add post-v1 columns to an existing DB if they are absent (idempotent)."""
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        for table, columns in _ADDED_COLUMNS.items():
            if table not in existing_tables:
                continue  # create_all just made it with the columns already
            present = {c["name"] for c in inspector.get_columns(table)}
            for name, ddl in columns.items():
                if name not in present:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))


def init_db() -> None:
    """Create data directories and all tables. Idempotent."""
    from backend import models  # noqa: F401 - register mappers

    if DB_PATH.parent and str(DB_PATH) != ":memory:":
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        RADIOGRAPH_DIR.mkdir(parents=True, exist_ok=True)
    models.Base.metadata.create_all(engine)
    _ensure_added_columns()
    models.ensure_schema_version(engine)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Transactional scope: commit on success, rollback on error (directive §38)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a session (commit/rollback handled per-request)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
