"""Session issue / lookup / revoke, and login throttling (security phase, C.1).

Design choices worth stating, because they are the ones that matter:

* **Only a hash of the session token is stored.** Same reasoning as passwords: a
  copied ``tw3.db`` must not hand the finder a working session. The raw token
  exists only in the cookie.
* **Absolute expiry AND idle timeout.** A clinic workstation gets walked away
  from; an 8-hour absolute cap bounds a stolen cookie, and a 30-minute idle
  timeout closes the common case.
* **Lockout is per account, not per IP.** The app is normally reached from one
  machine, so IP throttling would be useless here while account lockout still
  stops password guessing. Lockout is time-boxed rather than permanent so a
  fat-fingered clinician is not locked out of a patient's record until an admin
  is found.
* **Failures are counted, successes reset the counter**, and both are written to
  SecurityEvent so a burst of failures is visible after the fact.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import APP_VERSION
from backend.models import SecurityEvent, User, UserSession

SESSION_COOKIE_NAME = "pcw_session"

SESSION_ABSOLUTE_LIFETIME = timedelta(hours=8)
SESSION_IDLE_TIMEOUT = timedelta(minutes=30)

MAX_FAILED_LOGINS = 5
LOCKOUT_DURATION = timedelta(minutes=15)

_TOKEN_BYTES = 32


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _naive(dt: datetime) -> datetime:
    """SQLite columns here are naive UTC; normalise before comparing/storing."""
    return dt.replace(tzinfo=None) if dt.tzinfo is not None else dt


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def record_security_event(db: Session, *, event_type: str, severity: str = "info",
                          username: str | None = None, user_id: int | None = None,
                          patient_id: int | None = None, client_host: str | None = None,
                          detail: str | None = None) -> None:
    db.add(SecurityEvent(
        event_type=event_type, severity=severity, username=username, user_id=user_id,
        patient_id=patient_id, client_host=client_host, detail=detail,
        application_version=APP_VERSION,
    ))


# ── lockout ─────────────────────────────────────────────────────────────────

def is_locked(user: User) -> bool:
    return user.locked_until is not None and _naive(_utcnow()) < user.locked_until


def register_failed_login(db: Session, user: User, *, client_host: str | None) -> None:
    user.failed_login_count = (user.failed_login_count or 0) + 1
    detail = f"failed_login_count={user.failed_login_count}"
    if user.failed_login_count >= MAX_FAILED_LOGINS:
        user.locked_until = _naive(_utcnow() + LOCKOUT_DURATION)
        record_security_event(
            db, event_type="lockout", severity="warn", username=user.username,
            user_id=user.id, client_host=client_host,
            detail=f"locked until {user.locked_until.isoformat()} after "
                   f"{user.failed_login_count} failed attempts",
        )
    else:
        record_security_event(
            db, event_type="login_failure", severity="warn", username=user.username,
            user_id=user.id, client_host=client_host, detail=detail,
        )


def register_successful_login(db: Session, user: User, *, client_host: str | None) -> None:
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = _naive(_utcnow())
    record_security_event(
        db, event_type="login_success", username=user.username, user_id=user.id,
        client_host=client_host,
    )


# ── sessions ────────────────────────────────────────────────────────────────

def create_session(db: Session, user: User, *, user_agent: str | None = None,
                   client_host: str | None = None) -> str:
    """Issue a session and return the RAW token (the only time it exists)."""
    token = secrets.token_urlsafe(_TOKEN_BYTES)
    now = _naive(_utcnow())
    db.add(UserSession(
        user_id=user.id,
        token_hash=hash_token(token),
        created_at=now,
        last_seen_at=now,
        expires_at=_naive(_utcnow() + SESSION_ABSOLUTE_LIFETIME),
        user_agent=(user_agent or "")[:256] or None,
        client_host=client_host,
    ))
    return token


def resolve_session(db: Session, token: str) -> tuple[User, UserSession] | None:
    """Return (user, session) for a live token, else None.

    Touches ``last_seen_at`` so the idle timeout tracks real activity. Returns
    None for every failure mode -- unknown, revoked, expired, idle, or belonging
    to a deactivated user -- so a caller cannot distinguish them.
    """
    if not token:
        return None
    row = db.execute(
        select(UserSession).where(UserSession.token_hash == hash_token(token))
    ).scalar_one_or_none()
    if row is None or row.revoked_at is not None:
        return None

    now = _naive(_utcnow())
    if now >= row.expires_at:
        return None
    if now - row.last_seen_at > SESSION_IDLE_TIMEOUT:
        row.revoked_at = now
        return None

    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        return None

    row.last_seen_at = now
    return user, row


def revoke_session(db: Session, token: str) -> bool:
    row = db.execute(
        select(UserSession).where(UserSession.token_hash == hash_token(token))
    ).scalar_one_or_none()
    if row is None or row.revoked_at is not None:
        return False
    row.revoked_at = _naive(_utcnow())
    return True


def revoke_all_for_user(db: Session, user_id: int) -> int:
    """Used when a password changes or an account is deactivated -- otherwise an
    already-stolen session would outlive the credential change that was made to
    stop it."""
    rows = db.execute(
        select(UserSession).where(UserSession.user_id == user_id)
        .where(UserSession.revoked_at.is_(None))
    ).scalars().all()
    now = _naive(_utcnow())
    for row in rows:
        row.revoked_at = now
    return len(rows)
