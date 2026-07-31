"""Shared test setup.

Two jobs.

1. Make ``tests/`` importable so every suite can share helpers (M6). pytest's
   prepend import mode inserts the directory of each collected file, so
   tests/frontend/ and tests/cvd/ land on sys.path but tests/ itself does not.
   This conftest existing here is what puts it there, which is what lets any
   suite do ``from _frontend_source import frontend_source`` instead of each one
   re-deriving the path to the frontend app.

2. Authenticate the API suites (security phase, C.1).

   Every endpoint now requires a session. Rather than teach 13 test files to log
   in, the ``current_user`` / ``clinical_access`` dependencies are overridden
   with a stub doctor via FastAPI's ``dependency_overrides`` -- the standard
   pattern, applied in one place.

   This is deliberately NOT ``PCW_AUTH_DISABLED``. That flag switches
   enforcement off process-wide, so the suite would stop exercising the guarded
   paths entirely and a regression that dropped a router guard would go
   unnoticed. With an override, enforcement stays wired up everywhere and only
   the identity is supplied.

   The authentication and authorisation suites opt OUT via the ``real_auth``
   fixture, so login, lockout, 401s and 403s are tested against the real thing.
"""
from __future__ import annotations

import pytest


@pytest.fixture(scope="session")
def stub_doctor():
    """An in-memory user standing in for a logged-in clinician.

    Role `doctor` because it can do the most clinically (including approving),
    so suites testing clinical behaviour are not blocked by permissions they are
    not trying to test. Anything asserting that a role CANNOT do something must
    use `real_auth` and a real user.
    """
    from backend.models import User
    from backend.security import roles

    return User(
        id=1, username="pytest-doctor", full_name="Pytest Doctor",
        password_hash="", role=roles.DOCTOR, is_active=True,
    )


@pytest.fixture(autouse=True)
def _authenticated_api(request, stub_doctor):
    """Supply an identity to every API test, unless it asked for `real_auth`."""
    if "real_auth" in request.fixturenames:
        yield
        return

    from backend.security.deps import clinical_access, current_user
    from backend.server import app

    app.dependency_overrides[current_user] = lambda: stub_doctor
    app.dependency_overrides[clinical_access] = lambda: stub_doctor
    try:
        yield
    finally:
        app.dependency_overrides.pop(current_user, None)
        app.dependency_overrides.pop(clinical_access, None)


@pytest.fixture
def real_auth():
    """Opt out of the stub identity: exercise real login/permission enforcement.

    Requesting this fixture suppresses the autouse override above (which checks
    for it by name) and clears anything another module left behind.
    """
    from backend.security.deps import clinical_access, current_user
    from backend.server import app

    app.dependency_overrides.pop(current_user, None)
    app.dependency_overrides.pop(clinical_access, None)
    yield
    app.dependency_overrides.pop(current_user, None)
    app.dependency_overrides.pop(clinical_access, None)
