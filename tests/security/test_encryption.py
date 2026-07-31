"""Identifiers are encrypted at rest (security phase, C.2).

The threat is a copied database file -- backup stick, support bundle, cloud sync
folder, stolen laptop. Clinical rows in that file are damaging; a column of
children's names is what makes a copy a reportable breach. These tests assert the
name is genuinely unreadable in the file, not merely wrapped by an ORM helper.
"""
from __future__ import annotations

import base64
import os

import pytest
from sqlalchemy import text

from backend.security import crypto


@pytest.fixture
def key(monkeypatch):
    monkeypatch.setenv(crypto.ENV_KEY, crypto.generate_key())
    crypto.reset_key_cache()
    yield
    crypto.reset_key_cache()


@pytest.fixture
def no_key(monkeypatch):
    monkeypatch.delenv(crypto.ENV_KEY, raising=False)
    crypto.reset_key_cache()
    yield
    crypto.reset_key_cache()


# ── primitives ──────────────────────────────────────────────────────────────

def test_roundtrip(key):
    ct = crypto.encrypt("Aarav Sharma", context="patient.name")
    assert crypto.decrypt(ct, context="patient.name") == "Aarav Sharma"


def test_ciphertext_does_not_contain_the_plaintext(key):
    assert "Aarav" not in crypto.encrypt("Aarav Sharma", context="patient.name")


def test_same_plaintext_encrypts_differently_each_time(key):
    """A random nonce per write. Otherwise equal names produce equal ciphertext
    and the column leaks which patients share a name."""
    a = crypto.encrypt("Same Name", context="patient.name")
    b = crypto.encrypt("Same Name", context="patient.name")
    assert a != b
    assert crypto.decrypt(a, context="patient.name") == crypto.decrypt(b, context="patient.name")


def test_tampering_is_detected(key):
    """GCM is authenticated: a corrupted value must fail loudly, not decrypt to
    garbage that then gets displayed as a patient name."""
    ct = crypto.encrypt("Aarav Sharma", context="patient.name")
    head, nonce, body = ct.rsplit(":", 2)
    flipped = base64.b64encode(bytes([base64.b64decode(body)[0] ^ 0xFF]) +
                               base64.b64decode(body)[1:]).decode()
    with pytest.raises(crypto.EncryptionError, match="authentication"):
        crypto.decrypt(f"{head}:{nonce}:{flipped}", context="patient.name")


def test_ciphertext_cannot_be_replayed_into_another_field(key):
    """The field name is additional authenticated data, so a name lifted from
    patient.name cannot be pasted into a note field and read back out."""
    ct = crypto.encrypt("Aarav Sharma", context="patient.name")
    with pytest.raises(crypto.EncryptionError):
        crypto.decrypt(ct, context="radiograph.note")


def test_wrong_key_cannot_decrypt(key, monkeypatch):
    ct = crypto.encrypt("Aarav Sharma", context="patient.name")
    monkeypatch.setenv(crypto.ENV_KEY, crypto.generate_key())
    crypto.reset_key_cache()
    with pytest.raises(crypto.EncryptionError):
        crypto.decrypt(ct, context="patient.name")


def test_encrypting_without_a_key_fails_loudly(no_key):
    assert crypto.encryption_available() is False
    with pytest.raises(crypto.EncryptionError, match=crypto.ENV_KEY):
        crypto.encrypt("Aarav Sharma", context="patient.name")


def test_malformed_key_is_rejected_with_a_useful_message(monkeypatch):
    monkeypatch.setenv(crypto.ENV_KEY, base64.b64encode(os.urandom(7)).decode())
    crypto.reset_key_cache()
    with pytest.raises(crypto.EncryptionError, match="32 bytes"):
        crypto.encryption_available()
    crypto.reset_key_cache()


def test_generated_key_is_the_right_size():
    assert len(base64.b64decode(crypto.generate_key())) == 32


# ── through the ORM, onto disk ──────────────────────────────────────────────

def test_patient_name_is_unreadable_in_the_database_file(tmp_path, key):
    """The claim that actually matters, checked by reading raw SQL.

    Uses a throwaway engine bound to the same ORM metadata rather than reloading
    backend.db. An earlier version reloaded the module to repoint TW3_DB_PATH,
    which permanently swapped the process-wide engine and silently broke twelve
    unrelated tests later in the run -- module reloads leak far outside the test
    that performs them.
    """
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import sessionmaker

    from backend.models import Base, Patient

    engine = create_engine(f"sqlite:///{(tmp_path / 'enc.db').as_posix()}")
    Base.metadata.create_all(engine)
    Local = sessionmaker(bind=engine, expire_on_commit=False)

    with Local() as db:
        db.add(Patient(patient_code="MRN-ENC", name="Aarav Sharma", sex_at_birth="boys"))
        db.commit()

    with Local() as db:
        raw = db.execute(
            text("SELECT name FROM patient WHERE patient_code='MRN-ENC'")
        ).scalar_one()
        assert crypto.is_encrypted(raw), "name was stored in clear"
        assert "Aarav" not in raw

        loaded = db.execute(
            select(Patient).where(Patient.patient_code == "MRN-ENC")
        ).scalar_one()
        assert loaded.name == "Aarav Sharma", "round-trip through the ORM failed"

        # The lookup key stays readable on purpose -- it is a pseudonym, and
        # encrypting it would make finding a record impossible without
        # decrypting every row.
        assert db.execute(
            text("SELECT patient_code FROM patient WHERE patient_code='MRN-ENC'")
        ).scalar_one() == "MRN-ENC"

    engine.dispose()


def test_legacy_plaintext_rows_still_read(key):
    """A database written before encryption existed must keep working, or the
    feature is a migration cliff rather than an upgrade."""
    col = crypto.EncryptedString(600, context="patient.name")
    assert col.process_result_value("Plain Old Name", None) == "Plain Old Name"


def test_already_encrypted_values_are_not_double_encrypted(key):
    col = crypto.EncryptedString(600, context="patient.name")
    once = col.process_bind_param("Aarav Sharma", None)
    twice = col.process_bind_param(once, None)
    assert twice == once
    assert col.process_result_value(twice, None) == "Aarav Sharma"


def test_without_a_key_the_column_degrades_to_plaintext(no_key):
    """Deliberate: the dev/demo workflow must still run. Safe only because it is
    visible -- /api/health reports encryption_at_rest and safe_for_patient_data."""
    col = crypto.EncryptedString(600, context="patient.name")
    assert col.process_bind_param("Aarav Sharma", None) == "Aarav Sharma"
