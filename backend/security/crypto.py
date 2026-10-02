"""Authenticated field encryption for direct identifiers (security phase, C.2).

Threat being addressed: the database is a single SQLite file that gets copied.
Onto a USB stick for a backup, into a support bundle, into a cloud sync folder,
or off a stolen laptop. Clinical rows in that file are damaging; a column of
children's *names* is the part that turns a copy into a reportable breach under
the DPDP Act. Separating identifiers from clinical data means an attacker who
gets the file gets measurements they cannot attach to a person.

AES-256-GCM via ``cryptography``. GCM is authenticated, so a tampered ciphertext
fails loudly instead of decrypting to garbage that then gets shown as a patient
name. Hand-rolling this was never an option -- there is no AEAD in the standard
library, and inventing one for a security control is malpractice.

Stored form (self-describing so the scheme can be rotated later):

    enc:v1:<nonce-b64>:<ciphertext-b64>

The field's own name is used as **additional authenticated data**, so a
ciphertext lifted from one column cannot be replayed into another -- a name
cannot be moved into a note field and back out as though it had always been
there.

Key management, stated plainly because it is the weak point of any scheme like
this: the key comes from ``PCW_ENCRYPTION_KEY`` (base64, 32 bytes). If it sits
in a .env file beside the database, this protects against a copied *database*,
not a copied *directory*. That is still worth having -- database files travel on
their own far more often than whole deployments -- but it is not full-disk
encryption and is not a substitute for it.
"""
from __future__ import annotations

import base64
import logging
import os
from functools import lru_cache

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import String, TypeDecorator

log = logging.getLogger(__name__)

ENV_KEY = "PCW_ENCRYPTION_KEY"
# Preferred: a path to a file holding the key, kept OUTSIDE the app folder (a USB
# key, another drive, an admin-only folder). Then a copied app directory --
# database plus .env -- no longer carries the key that unlocks it.
ENV_KEY_FILE = "PCW_ENCRYPTION_KEY_FILE"
_PREFIX = "enc:v1:"
_NONCE_BYTES = 12  # GCM standard; never reused because it is random per write
_KEY_BYTES = 32


class EncryptionError(RuntimeError):
    """Raised when encryption is required but unavailable, or decryption fails."""


def generate_key() -> str:
    """A fresh base64 key, for `python -m backend.security.crypto`."""
    return base64.b64encode(os.urandom(_KEY_BYTES)).decode("ascii")


def _raw_key() -> tuple[str, str]:
    """(base64 key or "", where it came from: 'file' | 'env' | 'none')."""
    path = os.environ.get(ENV_KEY_FILE, "").strip()
    if path:
        try:
            with open(path, encoding="utf-8") as fh:
                return fh.read().strip(), "file"
        except OSError as exc:
            raise EncryptionError(f"{ENV_KEY_FILE} is set but unreadable ({exc})") from exc
    raw = os.environ.get(ENV_KEY, "").strip()
    return raw, ("env" if raw else "none")


def key_location() -> dict:
    """Where the key lives, and whether that defeats the purpose.

    The key protects a COPIED database. If it sits inside the application folder
    -- in the .env file or a key file there -- copying the folder copies both.
    """
    from pathlib import Path
    app_root = Path(__file__).resolve().parents[2]
    raw, source = _raw_key()
    beside = False
    if source == "file":
        beside = app_root in Path(os.environ[ENV_KEY_FILE]).resolve().parents
    elif source == "env":
        env_file = app_root / ".env"
        beside = env_file.exists() and ENV_KEY in env_file.read_text(encoding="utf-8", errors="ignore")
    return {"source": source, "inside_app_folder": beside}


@lru_cache(maxsize=1)
def _key() -> bytes | None:
    raw, _source = _raw_key()
    if not raw:
        return None
    try:
        key = base64.b64decode(raw)
    except Exception as exc:
        raise EncryptionError(f"{ENV_KEY} is not valid base64: {exc}") from exc
    if len(key) != _KEY_BYTES:
        raise EncryptionError(
            f"{ENV_KEY} must decode to {_KEY_BYTES} bytes, got {len(key)}. "
            "Generate one with: python -m backend.security.crypto"
        )
    return key


def encryption_available() -> bool:
    return _key() is not None


def reset_key_cache() -> None:
    """Test seam -- the key is read once per process in normal operation."""
    _key.cache_clear()


def is_encrypted(value: str | None) -> bool:
    return isinstance(value, str) and value.startswith(_PREFIX)


def encrypt(plaintext: str, *, context: str) -> str:
    key = _key()
    if key is None:
        raise EncryptionError(
            f"{ENV_KEY} is not set, so identifying fields cannot be encrypted. "
            "Generate one with: python -m backend.security.crypto"
        )
    nonce = os.urandom(_NONCE_BYTES)
    ct = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), context.encode("utf-8"))
    return _PREFIX + base64.b64encode(nonce).decode() + ":" + base64.b64encode(ct).decode()


def decrypt(stored: str, *, context: str) -> str:
    key = _key()
    if key is None:
        raise EncryptionError(
            f"stored value is encrypted but {ENV_KEY} is not set -- the data is "
            "unreadable without the key it was written with."
        )
    try:
        _, _, nonce_b64, ct_b64 = stored.split(":", 3)
        nonce = base64.b64decode(nonce_b64)
        ct = base64.b64decode(ct_b64)
        return AESGCM(key).decrypt(nonce, ct, context.encode("utf-8")).decode("utf-8")
    except InvalidTag as exc:
        raise EncryptionError(
            "decryption failed authentication -- the value was tampered with, "
            "written under a different key, or copied from another field."
        ) from exc
    except EncryptionError:
        raise
    except Exception as exc:
        raise EncryptionError(f"malformed encrypted value: {exc}") from exc


class EncryptedString(TypeDecorator):
    """Transparently encrypt a column at rest.

    Service and API code is unchanged: it reads and writes plain strings.

    Reads pass through values that are NOT in the encrypted form, so a database
    written before this existed keeps working and can be migrated in place
    (``python -m backend.security.crypto --migrate``) rather than needing a
    rebuild. Writes always encrypt when a key is configured.

    When no key is configured the column degrades to plaintext rather than
    refusing to start -- the project's dev/demo workflow has always been "run one
    command and type numbers into it". That is safe only because it is visible:
    /api/health reports ``encryption_at_rest``, and the security test suite fails
    if a production-shaped configuration (auth on) has encryption off.
    """

    impl = String
    cache_ok = True

    def __init__(self, length: int | None = None, *, context: str = "field", **kw):
        super().__init__(length=length, **kw)
        self.context = context

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if is_encrypted(value):
            return value  # already ciphertext; do not double-encrypt
        if not encryption_available():
            return value
        return encrypt(str(value), context=self.context)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if not is_encrypted(value):
            return value  # legacy plaintext row
        return decrypt(value, context=self.context)


def migrate_plaintext(db, model, column_name: str) -> int:
    """Re-save rows whose column is still plaintext, so they become ciphertext.

    Reading a row decrypts (or passes through) and writing it back encrypts, so
    this is a read-modify-write with no bespoke crypto in the migration itself.
    """
    from sqlalchemy import select

    if not encryption_available():
        raise EncryptionError(f"{ENV_KEY} is not set; nothing to migrate to")
    changed = 0
    for row in db.execute(select(model)).scalars().all():
        value = getattr(row, column_name)
        if value is None:
            continue
        setattr(row, column_name, value)  # forces re-bind through the type
        changed += 1
    db.flush()
    return changed


if __name__ == "__main__":  # pragma: no cover
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--migrate", action="store_true",
                        help="encrypt existing plaintext identifier columns in place")
    args = parser.parse_args()

    if not args.migrate:
        print(f"{ENV_KEY}={generate_key()}")
        print("\nStore this in .env (which is gitignored). Losing it makes every")
        print("encrypted identifier permanently unreadable -- back it up separately")
        print("from the database, or the two travel together and protect nothing.")
    else:
        from backend.db import session_scope
        from backend.models import Patient

        with session_scope() as db:
            n = migrate_plaintext(db, Patient, "name")
        print(f"re-encrypted {n} patient name(s)")
