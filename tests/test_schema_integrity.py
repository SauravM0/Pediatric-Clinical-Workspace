"""Schema versioning + hand-rolled-migration integrity (M0.1, M0.2).

This project deliberately has no Alembic: it is a single-file local SQLite app
whose "one command to run" property is worth protecting. Migration is therefore
``models.Base.metadata.create_all()`` (which covers *new tables* on any DB) plus
a hand-maintained ``db._ADDED_COLUMNS`` map (which covers *new columns* on
already-populated DBs, via idempotent ALTER TABLE ADD COLUMN).

That arrangement works, but it has one silent failure mode: a developer adds a
``mapped_column`` to an existing model and forgets ``_ADDED_COLUMNS``. Fresh
databases get the column from create_all -- so the whole test suite passes --
while every real, previously-initialised database raises
``OperationalError: no such column`` at query time. The suite here closes that
gap, giving the one safety property Alembic would have provided without any of
its operational surface.

It also pins the M0.1 fix: schema versions are APPENDED on change, never
written once and left stale.
"""
import os
import tempfile

os.environ.setdefault("TW3_DB_PATH", os.path.join(tempfile.mkdtemp(), "schema_test.db"))

import pytest
from sqlalchemy import inspect, text

from backend import models
from backend.db import _ADDED_COLUMNS, _ensure_added_columns, engine, init_db

# ---------------------------------------------------------------------------
# Frozen baseline: the column set of every table as shipped in schema v3
# (APP_VERSION 1.4.0, 26 July 2026).
#
# Purpose: anything added to these tables AFTER v3 must appear in
# _ADDED_COLUMNS, or existing databases break. Columns already listed here are
# either original or were correctly migrated at the time.
#
# WHEN YOU ADD A COLUMN: add it to the model, add it to db._ADDED_COLUMNS, and
# leave this baseline alone -- it is a historical record, not a mirror of the
# current schema. Only bump it when cutting a release that everyone re-installs
# from scratch (which, for a local-first app, is essentially never).
# ---------------------------------------------------------------------------
_V3_BASELINE: dict[str, frozenset[str]] = {
    "adjudication_item": frozenset({
        "bone_code", "created_at", "film_key", "id", "n_readers", "reason",
        "resolved_at", "resolved_by", "resolved_stage", "stage_system", "status",
        "updated_at", "votes_json",
    }),
    "audit_event": frozenset({
        "actor", "application_version", "assessment_id", "event_type", "id",
        "model_version", "new_value", "patient_id", "previous_value", "reason",
        "timestamp",
    }),
    "bone_age_feedback": frozenset({
        "ai_estimate_months", "ai_model_version", "application_version",
        "assessment_id", "chronological_age_months", "confidence",
        "corrected_age_months", "created_at", "id", "image_domain", "image_hash",
        "method", "note", "radiograph_id", "rater_id", "sex",
    }),
    "bone_assessment": frozenset({
        "ai_stage_probabilities", "ai_suggested_stage", "assessment_id",
        "bone_code", "bone_group", "confirmed_stage", "created_at",
        "doctor_modified_ai_result", "doctor_stage", "id", "localisation_box",
        "localisation_confidence", "modification_reason", "rater_id",
        "sex_specific_score", "stage_confidence", "updated_at",
    }),
    "model_release": frozenset({
        "application_version", "beat_incumbent", "created_at",
        "dataset_manifest_checksum", "gates_passed", "id", "incumbent_version",
        "metrics_json", "model_card_path", "model_kind", "reasons",
        "signed_off_at", "signed_off_by", "status", "verdict_passed", "version",
    }),
    "patient": frozenset({
        "created_at", "date_of_birth", "id", "name", "patient_code",
        "sex_at_birth", "updated_at",
    }),
    "radiograph": frozenset({
        "anonymisation_status", "bit_depth", "consent_status", "created_at",
        "height", "id", "image_hash", "internal_file_path", "laterality",
        "modality", "original_filename", "patient_id", "quality_flags",
        "quality_status", "source_domain", "source_format", "study_date", "width",
    }),
    "schema_version": frozenset({"applied_at", "id", "version"}),
    "tw3_assessment": frozenset({
        "application_version", "approved_at", "approved_by", "assessment_method",
        "assessment_status", "bone_age_difference_months", "bone_age_months",
        "bone_age_years", "carpal_bone_age_months", "chronological_age_months",
        "created_at", "doctor_approved", "id", "model_version", "patient_id",
        "quality_status", "radiograph_id", "read_round", "reader_id", "revision",
        "scoring_table_version", "sex_at_birth", "stage_system", "supersedes_id",
        "total_carpal_score", "total_rus_score", "updated_at",
    }),
}


@pytest.fixture(scope="module", autouse=True)
def _db():
    init_db()


# ── M0.2 — migration drift ──────────────────────────────────────────────────

def test_every_post_baseline_column_is_in_added_columns():
    """The core guard: a mapped column that create_all() would add to a fresh DB
    but _ensure_added_columns() would NOT add to an existing one."""
    missing: list[str] = []
    for table_name, table in models.Base.metadata.tables.items():
        baseline = _V3_BASELINE.get(table_name)
        if baseline is None:
            continue  # wholly new table -- create_all() handles it on every DB
        migrated = set(_ADDED_COLUMNS.get(table_name, {}))
        for col in table.columns:
            if col.name not in baseline and col.name not in migrated:
                missing.append(f"{table_name}.{col.name}")

    assert not missing, (
        "These columns are mapped on the model but are neither in the v3 baseline "
        "nor in db._ADDED_COLUMNS:\n  " + "\n  ".join(missing) + "\n\n"
        "A fresh database gets them from create_all(), so the test suite passes, "
        "but every existing database will raise 'no such column' at query time. "
        "Add each to db._ADDED_COLUMNS with a nullable/defaulted DDL."
    )


def test_added_columns_entries_all_exist_on_a_model():
    """Reverse direction: catches typos and columns renamed/removed on the model
    while a stale _ADDED_COLUMNS entry keeps ALTERing a column nothing maps."""
    stale: list[str] = []
    for table_name, columns in _ADDED_COLUMNS.items():
        table = models.Base.metadata.tables.get(table_name)
        assert table is not None, f"_ADDED_COLUMNS references unknown table {table_name!r}"
        mapped = {c.name for c in table.columns}
        stale.extend(f"{table_name}.{name}" for name in columns if name not in mapped)

    assert not stale, (
        "_ADDED_COLUMNS names columns that no model maps: " + ", ".join(stale) +
        " -- typo, or the model changed and this entry was left behind."
    )


def test_added_columns_are_nullable_or_defaulted():
    """SQLite cannot ADD a NOT NULL column without a DEFAULT to a populated table;
    it fails at migration time on exactly the databases that have real data."""
    offenders: list[str] = []
    for table_name, columns in _ADDED_COLUMNS.items():
        for name, ddl in columns.items():
            upper = ddl.upper()
            if "NOT NULL" in upper and "DEFAULT" not in upper:
                offenders.append(f"{table_name}.{name}: {ddl}")

    assert not offenders, (
        "NOT NULL without DEFAULT in _ADDED_COLUMNS:\n  " + "\n  ".join(offenders) +
        "\nSQLite rejects this on any table that already has rows."
    )


def test_migration_round_trip_restores_dropped_columns():
    """End-to-end proof that _ensure_added_columns() actually repairs a legacy DB.

    Physically drops every _ADDED_COLUMNS column (simulating a database created
    before they existed), re-runs the migration, and asserts each one returns.
    This exercises the real ALTER path rather than trusting the map by inspection.
    """
    inspector = inspect(engine)
    targets = {
        table: [c for c in cols if c in {x["name"] for x in inspector.get_columns(table)}]
        for table, cols in _ADDED_COLUMNS.items()
        if table in set(inspector.get_table_names())
    }
    assert any(targets.values()), "no migratable columns present to exercise"

    with engine.begin() as conn:
        for table, cols in targets.items():
            for name in cols:
                conn.execute(text(f"ALTER TABLE {table} DROP COLUMN {name}"))

    after_drop = inspect(engine)
    for table, cols in targets.items():
        present = {c["name"] for c in after_drop.get_columns(table)}
        assert not (set(cols) & present), f"{table}: drop did not take effect"

    _ensure_added_columns()

    restored = inspect(engine)
    for table, cols in targets.items():
        present = {c["name"] for c in restored.get_columns(table)}
        for name in cols:
            assert name in present, (
                f"{table}.{name} was not restored by _ensure_added_columns() -- "
                "the hand-rolled migration does not actually repair a legacy DB."
            )


# ── M0.1 — schema version is appended, not written once ─────────────────────

def test_schema_version_is_recorded():
    assert models.current_schema_version(engine) == models.DB_SCHEMA_VERSION


def test_schema_version_appends_on_change(monkeypatch):
    """Regression guard for the confirmed write-once bug.

    ensure_schema_version() used to insert only when the table was empty, so the
    recorded version froze at whatever the first init wrote. Verified before the
    fix: a DB created at "3" still reported "3" after the constant was bumped to
    "99" and init_db() re-run -- silently falsifying config.py's reproducibility
    contract.
    """
    before = models.current_schema_version(engine)

    # models.py does `from backend.config import DB_SCHEMA_VERSION`, so the name
    # is bound in models -- patch it there, not on config.
    monkeypatch.setattr(models, "DB_SCHEMA_VERSION", "999-test")
    models.ensure_schema_version(engine)

    assert models.current_schema_version(engine) == "999-test", (
        "schema version did not advance -- ensure_schema_version() is write-once again"
    )

    # Idempotent: re-running at the same version must not append a duplicate.
    from sqlalchemy import func, select

    from backend.db import SessionLocal

    with SessionLocal() as db:
        count_at_999 = db.execute(
            select(func.count()).select_from(models.SchemaVersion)
            .where(models.SchemaVersion.version == "999-test")
        ).scalar_one()
    models.ensure_schema_version(engine)
    with SessionLocal() as db:
        assert db.execute(
            select(func.count()).select_from(models.SchemaVersion)
            .where(models.SchemaVersion.version == "999-test")
        ).scalar_one() == count_at_999, "re-init appended a duplicate version row"

    # History is preserved, not overwritten -- an old result stays attributable
    # to the schema that produced it.
    from sqlalchemy import select as _select

    with SessionLocal() as db:
        versions = [
            r.version for r in
            db.execute(_select(models.SchemaVersion).order_by(models.SchemaVersion.id)).scalars()
        ]
    assert before in versions and versions[-1] == "999-test"
