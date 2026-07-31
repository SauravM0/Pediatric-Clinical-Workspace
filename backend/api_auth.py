"""Authentication and user administration endpoints (security phase, C.1).

Notes on choices a reviewer should check:

* Login answers identically for "no such user", "wrong password" and
  "deactivated account", and burns equivalent scrypt work in each case
  (passwords.verify_dummy). Otherwise the response distinguishes real staff
  usernames from typos.
* The session cookie is HttpOnly (so page scripts cannot read it), SameSite=Lax
  (so a third-party page cannot ride it), and Secure whenever the request did
  not arrive over plain localhost.
* Changing a password revokes every existing session for that user. A password
  change that leaves the stolen session alive does not achieve anything.
* Only an admin may create or modify accounts, and an admin cannot approve
  clinical results -- see security/roles.py for why that is not an oversight.
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models import SecurityEvent, User
from backend.security import roles
from backend.security.deps import auth_disabled, client_host, current_user, require
from backend.security.passwords import (
    MIN_PASSWORD_LENGTH,
    PasswordError,
    hash_password,
    needs_rehash,
    verify_dummy,
    verify_password,
)
from backend.security.sessions import (
    SESSION_ABSOLUTE_LIFETIME,
    SESSION_COOKIE_NAME,
    create_session,
    is_locked,
    record_security_event,
    register_failed_login,
    register_successful_login,
    revoke_all_for_user,
    revoke_session,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# One message for every failure mode -- see module docstring.
_LOGIN_FAILED = "invalid username or password"


def _commit_then_fail(db: Session, code: int, detail: str) -> None:
    """Persist security state, THEN raise.

    ``get_db`` commits on success and rolls back on exception. That is right for
    clinical writes -- a failed request must not leave half a record -- but it is
    exactly wrong for the bookkeeping that a *failure* produces: raising straight
    after ``register_failed_login`` rolled the counter back, so the lockout never
    engaged and an attacker had unlimited password attempts. Same for the
    security-event rows that make an attack visible afterwards.

    Committing first is safe here because nothing else is in flight on this
    session at this point: the request is being rejected, and the only pending
    changes are the counter and the audit row we intend to keep.
    """
    db.commit()
    raise HTTPException(code, detail)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=1024)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=1024)
    new_password: str = Field(min_length=1, max_length=1024)


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=1, max_length=1024)
    role: str
    full_name: Optional[str] = None
    must_change_password: bool = True


class UpdateUserRequest(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None
    full_name: Optional[str] = None
    reset_password: Optional[str] = None


def _is_secure_request(request: Request) -> bool:
    """Whether to mark the cookie Secure. Localhost over plain http is the
    documented dev workflow, so requiring Secure there would break login without
    improving anything -- nothing is on the wire."""
    if request.url.scheme == "https":
        return True
    host = (request.client.host if request.client else "") or ""
    return host not in ("127.0.0.1", "::1", "localhost", "testclient")


def _set_session_cookie(request: Request, response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=int(SESSION_ABSOLUTE_LIFETIME.total_seconds()),
        httponly=True,
        samesite="lax",
        secure=_is_secure_request(request),
        path="/",
    )


def _public_user(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
        "must_change_password": user.must_change_password,
        "permissions": sorted(roles.permissions_for(user.role)),
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
    }


@router.post("/login")
def login(request: Request, response: Response, body: LoginRequest,
          db: Session = Depends(get_db)) -> dict[str, Any]:
    host = client_host(request)
    user = db.execute(
        select(User).where(User.username == body.username.strip())
    ).scalar_one_or_none()

    if user is None:
        verify_dummy()  # equalise timing against a real verification
        record_security_event(db, event_type="login_failure", severity="warn",
                              username=body.username[:64], client_host=host,
                              detail="unknown username")
        _commit_then_fail(db, status.HTTP_401_UNAUTHORIZED, _LOGIN_FAILED)

    if is_locked(user):
        record_security_event(db, event_type="login_failure", severity="warn",
                              username=user.username, user_id=user.id, client_host=host,
                              detail="attempt while locked out")
        _commit_then_fail(
            db, status.HTTP_429_TOO_MANY_REQUESTS,
            "account temporarily locked after repeated failed logins; try again later",
        )

    if not verify_password(body.password, user.password_hash) or not user.is_active:
        # Deactivated accounts take this branch on purpose: a former employee
        # should not be able to tell a disabled account from a wrong password.
        register_failed_login(db, user, client_host=host)
        _commit_then_fail(db, status.HTTP_401_UNAUTHORIZED, _LOGIN_FAILED)

    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(body.password)

    register_successful_login(db, user, client_host=host)
    token = create_session(db, user, user_agent=request.headers.get("user-agent"),
                           client_host=host)
    db.flush()
    _set_session_cookie(request, response, token)
    return {"authenticated": True, "user": _public_user(user)}


@router.post("/logout")
def logout(request: Request, response: Response,
           db: Session = Depends(get_db)) -> dict[str, Any]:
    token = request.cookies.get(SESSION_COOKIE_NAME, "")
    revoked = revoke_session(db, token)
    if revoked:
        record_security_event(db, event_type="logout", client_host=client_host(request))
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return {"authenticated": False, "session_revoked": revoked}


@router.get("/me")
def me(user: User = Depends(current_user)) -> dict[str, Any]:
    return {"authenticated": True, "auth_enforced": not auth_disabled(),
            "user": _public_user(user)}


@router.post("/change-password")
def change_password(request: Request, body: ChangePasswordRequest,
                    user: User = Depends(current_user),
                    db: Session = Depends(get_db)) -> dict[str, Any]:
    if not verify_password(body.current_password, user.password_hash):
        record_security_event(db, event_type="login_failure", severity="warn",
                              username=user.username, user_id=user.id,
                              client_host=client_host(request),
                              detail="wrong current password on change-password")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "current password is incorrect")
    try:
        user.password_hash = hash_password(body.new_password)
    except PasswordError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    user.must_change_password = False
    from backend.security.sessions import _naive, _utcnow  # local: internal helpers

    user.password_changed_at = _naive(_utcnow())
    # Every other session for this user dies with the old password.
    revoked = revoke_all_for_user(db, user.id)
    db.flush()
    return {"changed": True, "sessions_revoked": revoked,
            "note": "all sessions were signed out; log in again"}


# ── user administration (admin only) ────────────────────────────────────────

@router.get("/users")
def list_users(db: Session = Depends(get_db),
               _: User = Depends(require(roles.MANAGE_USERS))) -> dict[str, Any]:
    rows = db.execute(select(User).order_by(User.username)).scalars().all()
    return {"users": [_public_user(u) for u in rows]}


@router.post("/users", status_code=201)
def create_user(body: CreateUserRequest, db: Session = Depends(get_db),
                actor: User = Depends(require(roles.MANAGE_USERS))) -> dict[str, Any]:
    if not roles.is_valid_role(body.role):
        raise HTTPException(422, f"role must be one of {roles.ALL_ROLES}")
    existing = db.execute(
        select(User).where(User.username == body.username.strip())
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(409, "username already exists")
    try:
        pw_hash = hash_password(body.password)
    except PasswordError as exc:
        raise HTTPException(422, str(exc)) from exc

    user = User(username=body.username.strip(), full_name=body.full_name,
                password_hash=pw_hash, role=body.role,
                must_change_password=body.must_change_password)
    db.add(user)
    db.flush()
    record_security_event(db, event_type="user_created", username=actor.username,
                          user_id=actor.id,
                          detail=f"created {user.username} with role {user.role}")
    return _public_user(user)


@router.patch("/users/{user_id}")
def update_user(user_id: int, body: UpdateUserRequest, db: Session = Depends(get_db),
                actor: User = Depends(require(roles.MANAGE_USERS))) -> dict[str, Any]:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "user not found")

    changes: list[str] = []
    if body.role is not None:
        if not roles.is_valid_role(body.role):
            raise HTTPException(422, f"role must be one of {roles.ALL_ROLES}")
        changes.append(f"role {user.role}->{body.role}")
        user.role = body.role
    if body.full_name is not None:
        user.full_name = body.full_name
    if body.is_active is not None and body.is_active != user.is_active:
        changes.append(f"is_active {user.is_active}->{body.is_active}")
        user.is_active = body.is_active
        if not body.is_active:
            # Deactivation must take effect now, not at session expiry.
            revoke_all_for_user(db, user.id)
    if body.reset_password is not None:
        try:
            user.password_hash = hash_password(body.reset_password)
        except PasswordError as exc:
            raise HTTPException(422, str(exc)) from exc
        user.must_change_password = True
        revoke_all_for_user(db, user.id)
        changes.append("password reset")

    if changes:
        record_security_event(db, event_type="user_updated", username=actor.username,
                              user_id=actor.id,
                              detail=f"{user.username}: {'; '.join(changes)}")
    db.flush()
    return _public_user(user)


@router.get("/security-events")
def security_events(limit: int = 100, db: Session = Depends(get_db),
                    _: User = Depends(require(roles.VIEW_SECURITY_LOG))) -> dict[str, Any]:
    limit = max(1, min(limit, 500))
    rows = db.execute(
        select(SecurityEvent).order_by(SecurityEvent.id.desc()).limit(limit)
    ).scalars().all()
    return {
        "events": [
            {"id": e.id, "type": e.event_type, "severity": e.severity,
             "username": e.username, "client_host": e.client_host,
             "detail": e.detail, "occurred_at": e.occurred_at.isoformat()}
            for e in rows
        ],
        "password_policy": {"min_length": MIN_PASSWORD_LENGTH},
    }
