"""Password hashing (security phase, C.1).

Uses ``hashlib.scrypt`` from the standard library. scrypt is memory-hard, so a
GPU/ASIC attacker gains far less than against a plain iterated hash, and using
stdlib avoids adding a native-build dependency to a project that must stay
``pip install -r requirements.txt`` simple on a clinic laptop.

Storage format (single string, self-describing so parameters can be raised later
without invalidating existing hashes):

    scrypt$<n>$<r>$<p>$<salt-b64>$<hash-b64>

Nothing here logs, prints, or returns a plaintext password.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass

# ~32 MB of memory per hash (128 * r * n). Deliberate: it makes offline cracking
# expensive while staying comfortable for a single interactive login on modest
# clinic hardware. Raise N (not r/p) if hardware improves -- the format records
# the parameters used, so old hashes keep verifying and are upgraded on next
# successful login (see needs_rehash).
_N = 2 ** 15
_R = 8
_P = 1
_SALT_BYTES = 16
_KEY_LEN = 32
# OpenSSL's default maxmem is 32 MB, which the parameters above sit right at the
# edge of; set it explicitly so hashing cannot fail on a stricter build.
_MAXMEM = 128 * _R * _N * 2 + (1 << 20)

_PREFIX = "scrypt"

# Minimum length only. Deliberately no composition rules (must-have-a-symbol
# etc.): they push users toward predictable substitutions and are not what
# current guidance recommends. Length plus lockout is the stronger pair.
MIN_PASSWORD_LENGTH = 12


class PasswordError(ValueError):
    """Raised for a malformed stored hash or a rejected new password."""


@dataclass(frozen=True)
class _Parsed:
    n: int
    r: int
    p: int
    salt: bytes
    digest: bytes


def _b64e(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _b64d(text: str) -> bytes:
    return base64.b64decode(text.encode("ascii"))


def _derive(password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=n, r=r, p=p,
        dklen=_KEY_LEN, maxmem=128 * r * n * 2 + (1 << 20),
    )


def validate_password_strength(password: str) -> None:
    """Raise PasswordError if the password is unacceptable. Length-based only."""
    if not isinstance(password, str) or len(password) < MIN_PASSWORD_LENGTH:
        raise PasswordError(
            f"password must be at least {MIN_PASSWORD_LENGTH} characters"
        )
    if len(password.encode("utf-8")) > 1024:
        # Bounds the work an unauthenticated caller can force us to do.
        raise PasswordError("password is too long (max 1024 bytes)")


def hash_password(password: str) -> str:
    validate_password_strength(password)
    salt = secrets.token_bytes(_SALT_BYTES)
    digest = _derive(password, salt, _N, _R, _P)
    return f"{_PREFIX}${_N}${_R}${_P}${_b64e(salt)}${_b64e(digest)}"


def _parse(stored: str) -> _Parsed:
    try:
        prefix, n, r, p, salt, digest = stored.split("$")
        if prefix != _PREFIX:
            raise ValueError(f"unsupported scheme {prefix!r}")
        return _Parsed(int(n), int(r), int(p), _b64d(salt), _b64d(digest))
    except Exception as exc:
        raise PasswordError(f"malformed password hash: {exc}") from exc


def verify_password(password: str, stored: str) -> bool:
    """Constant-time verify. False (never an exception) on a bad password."""
    try:
        parsed = _parse(stored)
    except PasswordError:
        return False
    if not isinstance(password, str) or not password:
        return False
    candidate = _derive(password, parsed.salt, parsed.n, parsed.r, parsed.p)
    return hmac.compare_digest(candidate, parsed.digest)


def needs_rehash(stored: str) -> bool:
    """True when a stored hash used weaker parameters than we now require, so a
    successful login can transparently upgrade it."""
    try:
        parsed = _parse(stored)
    except PasswordError:
        return True
    return (parsed.n, parsed.r, parsed.p) != (_N, _R, _P)


# A real hash of a random password, computed once at import. verify_dummy() runs
# the same scrypt work as a real verification so that logging in as a
# NON-EXISTENT user costs the same wall-clock time as an existing one. Without
# it, response timing reveals which usernames exist -- and in a clinic those are
# staff names.
_DUMMY_HASH = hash_password(secrets.token_urlsafe(32))


def verify_dummy() -> bool:
    """Burn equivalent work for an unknown user. Always returns False."""
    verify_password("not-the-password-anyone-typed", _DUMMY_HASH)
    return False
