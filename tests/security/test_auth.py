"""Authentication and authorisation, against the real enforcement path (C.1).

Every test here takes the ``real_auth`` fixture, which suppresses the stub
identity the rest of the suite uses. Without that these would pass vacuously --
the whole point is to exercise login, lockout, 401 and 403 for real.
"""
from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.db import SessionLocal, init_db, session_scope
from backend.models import SecurityEvent, User, UserSession
from backend.security import roles
from backend.security.passwords import (
    MIN_PASSWORD_LENGTH,
    PasswordError,
    hash_password,
    needs_rehash,
    verify_password,
)
from backend.security.sessions import (
    MAX_FAILED_LOGINS,
    SESSION_COOKIE_NAME,
    SESSION_IDLE_TIMEOUT,
    _naive,
    _utcnow,
    resolve_session,
)
from backend.server import app

GOOD_PASSWORD = "correct-horse-battery-staple"


@pytest.fixture(scope="module", autouse=True)
def _schema():
    init_db()


@pytest.fixture
def client():
    return TestClient(app)


def _make_user(username: str, role: str, password: str = GOOD_PASSWORD,
               active: bool = True) -> int:
    """Create the user, or reset an existing one of the same name.

    Deliberately does NOT delete-and-recreate: sessions and security events
    reference app_user, so a delete trips the foreign key (which is enforced --
    see db.py's PRAGMA hook). Resetting in place is also closer to reality.
    """
    with session_scope() as db:
        u = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
        if u is None:
            u = User(username=username, password_hash=hash_password(password),
                     role=role, is_active=active)
            db.add(u)
        else:
            u.password_hash = hash_password(password)
            u.role = role
            u.is_active = active
            u.failed_login_count = 0
            u.locked_until = None
        db.flush()
        return u.id


# ── password primitives ─────────────────────────────────────────────────────

def test_password_verifies_and_rejects():
    stored = hash_password(GOOD_PASSWORD)
    assert verify_password(GOOD_PASSWORD, stored)
    assert not verify_password(GOOD_PASSWORD + "x", stored)
    assert not verify_password("", stored)


def test_password_hash_is_salted():
    """Two users with the same password must not share a hash, or one cracked
    password reveals every account that reused it."""
    assert hash_password(GOOD_PASSWORD) != hash_password(GOOD_PASSWORD)


def test_plaintext_never_appears_in_the_stored_hash():
    assert GOOD_PASSWORD not in hash_password(GOOD_PASSWORD)


def test_short_passwords_are_rejected():
    with pytest.raises(PasswordError, match=str(MIN_PASSWORD_LENGTH)):
        hash_password("short")


def test_malformed_stored_hash_fails_closed():
    for junk in ("", "not-a-hash", "scrypt$bad", "$$$$$"):
        assert verify_password(GOOD_PASSWORD, junk) is False
        assert needs_rehash(junk) is True


# ── login ───────────────────────────────────────────────────────────────────

def test_login_succeeds_and_sets_a_secure_cookie(real_auth, client):
    _make_user("dr_login", roles.DOCTOR)
    r = client.post("/api/auth/login", json={"username": "dr_login", "password": GOOD_PASSWORD})
    assert r.status_code == 200, r.text
    assert r.json()["user"]["role"] == roles.DOCTOR

    cookie = r.headers.get("set-cookie", "").lower()
    assert SESSION_COOKIE_NAME in cookie
    assert "httponly" in cookie, "session cookie must not be readable by page scripts"
    assert "samesite=lax" in cookie, "cookie must not ride a cross-site request"


def test_raw_session_token_is_not_stored(real_auth, client):
    """A copied database must not yield a usable session."""
    _make_user("dr_token", roles.DOCTOR)
    r = client.post("/api/auth/login", json={"username": "dr_token", "password": GOOD_PASSWORD})
    token = client.cookies.get(SESSION_COOKIE_NAME)
    assert token
    with SessionLocal() as db:
        assert db.execute(
            select(UserSession).where(UserSession.token_hash == token)
        ).scalar_one_or_none() is None, "the raw token is in the database"


@pytest.mark.parametrize("username,password", [
    ("dr_wrong", "definitely-not-the-password"),
    ("no-such-user-at-all", GOOD_PASSWORD),
])
def test_bad_credentials_give_one_indistinguishable_answer(real_auth, client, username, password):
    """Unknown user and wrong password must be indistinguishable, or the endpoint
    becomes a directory of clinic staff usernames."""
    _make_user("dr_wrong", roles.DOCTOR)
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 401
    assert r.json()["detail"] == "invalid username or password"


def test_deactivated_account_cannot_log_in(real_auth, client):
    _make_user("dr_gone", roles.DOCTOR, active=False)
    r = client.post("/api/auth/login", json={"username": "dr_gone", "password": GOOD_PASSWORD})
    assert r.status_code == 401
    assert r.json()["detail"] == "invalid username or password"


def test_repeated_failures_lock_the_account(real_auth, client):
    _make_user("dr_lock", roles.DOCTOR)
    for _ in range(MAX_FAILED_LOGINS):
        assert client.post("/api/auth/login",
                           json={"username": "dr_lock", "password": "wrong"}).status_code == 401
    # Even the CORRECT password is refused while locked.
    r = client.post("/api/auth/login", json={"username": "dr_lock", "password": GOOD_PASSWORD})
    assert r.status_code == 429
    with SessionLocal() as db:
        assert db.execute(
            select(SecurityEvent).where(SecurityEvent.event_type == "lockout")
            .where(SecurityEvent.username == "dr_lock")
        ).scalars().first() is not None, "lockout was not recorded in the security log"


def test_successful_login_clears_the_failure_counter(real_auth, client):
    uid = _make_user("dr_reset", roles.DOCTOR)
    client.post("/api/auth/login", json={"username": "dr_reset", "password": "wrong"})
    client.post("/api/auth/login", json={"username": "dr_reset", "password": GOOD_PASSWORD})
    with SessionLocal() as db:
        assert db.get(User, uid).failed_login_count == 0


# ── enforcement ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("method,path", [
    ("get", "/api/growth/chart?measure=height&sex=girls"),
    ("get", "/api/growth/point?measure=height&sex=girls&age=9&value=131.5"),
    ("get", "/api/bone-age/config"),
    ("post", "/api/bone-age/score"),
    ("post", "/api/cvd/qrisk3"),
])
def test_clinical_endpoints_reject_anonymous_callers(real_auth, client, method, path):
    r = getattr(client, method)(path, **({"json": {}} if method == "post" else {}))
    assert r.status_code == 401, f"{path} answered {r.status_code} without a session"


def test_health_is_reachable_without_a_session(real_auth, client):
    """A liveness probe must work before login; it exposes no patient data."""
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_health_discloses_the_security_posture(real_auth, client):
    body = client.get("/api/health").json()
    assert body["auth_enabled"] is True
    assert "encryption_at_rest" in body and "safe_for_patient_data" in body


def test_logout_revokes_the_session(real_auth, client):
    _make_user("dr_out", roles.DOCTOR)
    client.post("/api/auth/login", json={"username": "dr_out", "password": GOOD_PASSWORD})
    assert client.get("/api/auth/me").status_code == 200
    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401


def test_idle_session_expires(real_auth, client):
    _make_user("dr_idle", roles.DOCTOR)
    client.post("/api/auth/login", json={"username": "dr_idle", "password": GOOD_PASSWORD})
    token = client.cookies.get(SESSION_COOKIE_NAME)

    with session_scope() as db:
        row = db.execute(select(UserSession)).scalars().all()[-1]
        row.last_seen_at = _naive(_utcnow() - SESSION_IDLE_TIMEOUT - timedelta(minutes=1))

    with SessionLocal() as db:
        assert resolve_session(db, token) is None, "an idle session still resolved"


def test_password_change_revokes_every_other_session(real_auth, client):
    _make_user("dr_pw", roles.DOCTOR)
    other = TestClient(app)
    other.post("/api/auth/login", json={"username": "dr_pw", "password": GOOD_PASSWORD})
    assert other.get("/api/auth/me").status_code == 200

    client.post("/api/auth/login", json={"username": "dr_pw", "password": GOOD_PASSWORD})
    r = client.post("/api/auth/change-password", json={
        "current_password": GOOD_PASSWORD, "new_password": "a-brand-new-long-password"})
    assert r.status_code == 200 and r.json()["changed"] is True

    assert other.get("/api/auth/me").status_code == 401, (
        "a session issued under the old password survived the change"
    )


# ── roles ───────────────────────────────────────────────────────────────────

def test_assistant_cannot_write_beyond_its_permission(real_auth, client):
    """An assistant may record data but not approve; admin may manage users but
    not approve either. Encoded as permissions, not a seniority ladder."""
    assert roles.has_permission(roles.ASSISTANT, roles.WRITE_CLINICAL)
    assert not roles.has_permission(roles.ASSISTANT, roles.APPROVE_CLINICAL)


def test_admin_cannot_approve_clinical_results():
    """Deliberate, and the most important line in roles.py: an admin is an IT
    function. Letting it sign off a bone age would put a non-clinician's name on
    a clinical record."""
    assert roles.has_permission(roles.ADMIN, roles.MANAGE_USERS)
    assert not roles.has_permission(roles.ADMIN, roles.APPROVE_CLINICAL)
    assert not roles.has_permission(roles.ADMIN, roles.WRITE_CLINICAL)


def test_doctor_cannot_manage_users():
    assert roles.has_permission(roles.DOCTOR, roles.APPROVE_CLINICAL)
    assert not roles.has_permission(roles.DOCTOR, roles.MANAGE_USERS)


def test_admin_is_denied_a_clinical_write_over_http(real_auth, client):
    _make_user("it_admin", roles.ADMIN)
    client.post("/api/auth/login", json={"username": "it_admin", "password": GOOD_PASSWORD})
    r = client.post("/api/bone-age/score", json={"sex": "boys", "stages": {}})
    assert r.status_code == 403
    assert "not permitted" in r.json()["detail"]

    with SessionLocal() as db:
        assert db.execute(
            select(SecurityEvent).where(SecurityEvent.event_type == "authz_denied")
        ).scalars().first() is not None, "a denied request was not recorded"


def test_assistant_may_read_and_write_but_not_approve(real_auth, client):
    _make_user("nurse", roles.ASSISTANT)
    client.post("/api/auth/login", json={"username": "nurse", "password": GOOD_PASSWORD})
    assert client.get("/api/bone-age/config").status_code == 200
    assert client.post("/api/bone-age/score",
                       json={"sex": "boys", "stages": {}}).status_code == 200
    r = client.post("/api/bone-age/assessments/999999/approve", json={"approved_by": "x"})
    assert r.status_code == 403, "an assistant approved a clinical result"


def test_only_admin_may_list_users(real_auth, client):
    _make_user("dr_nolist", roles.DOCTOR)
    client.post("/api/auth/login", json={"username": "dr_nolist", "password": GOOD_PASSWORD})
    assert client.get("/api/auth/users").status_code == 403
