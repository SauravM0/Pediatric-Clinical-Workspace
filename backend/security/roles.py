"""Roles and the permissions each one carries (security phase, C.1).

Three roles, chosen to match how a paediatric clinic actually works rather than
a generic admin/user split:

* ``assistant`` -- front desk / nurse. Records measurements and uploads films.
  Cannot approve a clinical result and cannot see the security log.
* ``doctor``    -- the treating clinician. Everything an assistant can do, plus
  approving assessments (the act that turns a draft into a clinical record) and
  handling data-subject requests.
* ``admin``     -- manages user accounts. Deliberately NOT a superset: an admin
  is an IT function, and giving it clinical approval rights would let a
  non-clinician sign off a bone age.

That last point is the reason this is an explicit permission map rather than an
ordered privilege level. Seniority ladders quietly grant clinical authority to
whoever sits at the top, which is exactly wrong here.
"""
from __future__ import annotations

from typing import Final

ADMIN: Final = "admin"
DOCTOR: Final = "doctor"
ASSISTANT: Final = "assistant"

ALL_ROLES: Final[tuple[str, ...]] = (ADMIN, DOCTOR, ASSISTANT)

# Permission vocabulary. Endpoints depend on these, never on a role name, so a
# future role only has to be added here.
READ_CLINICAL: Final = "read_clinical"
WRITE_CLINICAL: Final = "write_clinical"
APPROVE_CLINICAL: Final = "approve_clinical"
MANAGE_USERS: Final = "manage_users"
VIEW_SECURITY_LOG: Final = "view_security_log"
MANAGE_DATA_RIGHTS: Final = "manage_data_rights"
MANAGE_MODELS: Final = "manage_models"

_PERMISSIONS: Final[dict[str, frozenset[str]]] = {
    ASSISTANT: frozenset({READ_CLINICAL, WRITE_CLINICAL}),
    DOCTOR: frozenset({
        READ_CLINICAL, WRITE_CLINICAL, APPROVE_CLINICAL,
        MANAGE_DATA_RIGHTS, MANAGE_MODELS,
    }),
    # Account administration and oversight -- NOT clinical approval.
    ADMIN: frozenset({
        READ_CLINICAL, MANAGE_USERS, VIEW_SECURITY_LOG, MANAGE_DATA_RIGHTS,
    }),
}


def permissions_for(role: str) -> frozenset[str]:
    return _PERMISSIONS.get(role, frozenset())


def has_permission(role: str, permission: str) -> bool:
    return permission in permissions_for(role)


def is_valid_role(role: str) -> bool:
    return role in _PERMISSIONS
