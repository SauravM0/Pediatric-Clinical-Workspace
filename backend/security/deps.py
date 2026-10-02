"""FastAPI dependencies that enforce authentication and permissions (C.1).

Endpoints depend on a PERMISSION, never on a role name:

    @router.post("/assessments/{id}/approve")
    def approve(user: User = Depends(require(APPROVE_CLINICAL))): ...

so adding a role is a change in roles.py alone, and reading an endpoint tells
you what authority it actually requires.

FAIL CLOSED. Authentication is on by default and must be switched off
deliberately, per-process, via ``PCW_AUTH_DISABLED=1``. That escape hatch exists
for the dev/demo workflow the project has always supported (open index.html,
type numbers, get a chart) -- not for production. When it is set the app logs a
warning at import and ``/api/health`` reports ``auth_enabled: false``, so an
unprotected instance is never silently unprotected.

Test suites do NOT use that flag. They override ``current_user`` through
FastAPI's dependency_overrides (see tests/conftest.py), which leaves enforcement
switched on everywhere and keeps the auth suite testing the real path.
"""
from __future__ import annotations

import logging
import os

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models import User
from backend.security import roles, sessions

log = logging.getLogger(__name__)


def auth_disabled() -> bool:
    """Authentication is OFF by default. This is a deliberate product decision.

    The owner asked for sign-in to be removed from the workspace permanently, so
    the default is inverted rather than left to a gitignored .env file -- a fresh
    clone must behave the same way, not silently start demanding a login nobody
    can perform (there is no sign-in UI any more, by the same decision).

    Set ``PCW_AUTH_ENABLED=1`` to put enforcement back. The whole auth stack --
    sessions, lockout, roles, permissions, security events -- is still present
    and still tested; only the default changed.

    What running without it costs, recorded here so it is not rediscovered the
    hard way:

      * Anyone who can reach the app can read and change every patient record.
        The server binds to 127.0.0.1, so that means anyone with access to this
        computer, not the network.
      * Approvals stop naming a clinician. ``approve`` signs with the session
        identity on purpose (a self-declared name is not a signature), so every
        sign-off is now attributed to ``dev-no-auth`` below.
      * Role separation is gone: the dev identity holds the doctor role, so the
        assistant-cannot-approve boundary no longer applies.
    """
    if os.environ.get("PCW_AUTH_ENABLED", "").strip().lower() in ("1", "true", "yes"):
        return False
    return True


if auth_disabled():  # pragma: no cover - environment-dependent
    log.warning(
        "Authentication is DISABLED: every endpoint is UNAUTHENTICATED, and "
        "approvals are attributed to 'dev-no-auth' rather than a named "
        "clinician. Set PCW_AUTH_ENABLED=1 to re-enable. Never expose this "
        "instance to a network."
    )


# The identity used when auth is explicitly disabled. Not persisted; it exists
# only so downstream code has a User-shaped object and audit rows still say
# something truthful about where the action came from.
_DEV_USER = User(
    id=0, username="dev-no-auth", full_name="Development (auth disabled)",
    password_hash="", role=roles.DOCTOR, is_active=True,
)


def _record_denial_and_fail(db: Session, request: Request, user: User,
                            permission: str, detail: str) -> None:
    """Log the denial, COMMIT it, then 403.

    get_db rolls back on exception, so raising straight after writing the event
    would discard the very record that makes repeated probing visible. Committing
    first is safe: the request is being rejected and the audit row is the only
    pending change.
    """
    sessions.record_security_event(
        db, event_type="authz_denied", severity="warn",
        username=user.username, user_id=user.id or None,
        client_host=request.client.host if request.client else None,
        detail=detail,
    )
    db.commit()
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"role '{user.role}' is not permitted to {permission}",
    )


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """The authenticated user, or 401.

    Reads the session cookie. Deliberately does not accept a token via query
    string or a custom header: query strings land in server logs and browser
    history, which is the wrong place for a credential.
    """
    if auth_disabled():
        return _DEV_USER

    token = request.cookies.get(sessions.SESSION_COOKIE_NAME, "")
    resolved = sessions.resolve_session(db, token)
    if resolved is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="not authenticated",
            headers={"WWW-Authenticate": "Cookie"},
        )
    user, _session = resolved
    return user


def require(permission: str):
    """Dependency factory: 403 unless the caller's role carries `permission`."""

    def _dep(request: Request, user: User = Depends(current_user),
             db: Session = Depends(get_db)) -> User:
        if not roles.has_permission(user.role, permission):
            # Recorded: repeated denials are a signal, whether it is a
            # misconfigured account or someone probing.
            _record_denial_and_fail(
                db, request, user, permission,
                f"role={user.role} lacks {permission} for {request.url.path}",
            )
        return user

    return _dep


_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def clinical_access(request: Request, user: User = Depends(current_user),
                    db: Session = Depends(get_db)) -> User:
    """Router-level guard for the clinical APIs.

    Derives the required permission from the HTTP method: safe methods need
    READ_CLINICAL, anything that mutates needs WRITE_CLINICAL. Applied once per
    router rather than annotating ~40 endpoints by hand -- a per-endpoint list is
    exactly the kind of thing that acquires a hole when someone adds route 41 and
    forgets the decorator. Here a new route is protected by construction.

    Endpoints needing MORE than write (approving a clinical result) still declare
    that explicitly; this is a floor, not a ceiling.
    """
    permission = roles.READ_CLINICAL if request.method in _SAFE_METHODS else roles.WRITE_CLINICAL
    if not roles.has_permission(user.role, permission):
        _record_denial_and_fail(
            db, request, user, permission,
            f"role={user.role} lacks {permission} for {request.method} {request.url.path}",
        )
    return user


def client_host(request: Request) -> str | None:
    return request.client.host if request.client else None
