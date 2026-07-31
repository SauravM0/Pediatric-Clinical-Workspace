"""Security package: authentication, roles, sessions, field encryption.

Added by the security phase, which the engineering report made a hard gate
before M2 (the longitudinal clinical record). Until M2 the product was
stateless for growth and single-user for bone age, which bounded the exposure;
M2 creates a persistent database of identified children, and that is a change of
risk class, not a change of degree.

Modules:
    passwords   scrypt hashing, constant-time verify, timing-equalised dummy
    roles       permission map (permissions, not a seniority ladder)
    sessions    session issue/resolve/revoke, lockout, security-event log
    deps        FastAPI dependencies -- fail closed
    crypto      authenticated field encryption for direct identifiers
"""
from .roles import (
    ADMIN,
    ALL_ROLES,
    APPROVE_CLINICAL,
    ASSISTANT,
    DOCTOR,
    MANAGE_DATA_RIGHTS,
    MANAGE_MODELS,
    MANAGE_USERS,
    READ_CLINICAL,
    VIEW_SECURITY_LOG,
    WRITE_CLINICAL,
    has_permission,
    is_valid_role,
    permissions_for,
)

__all__ = [
    "ADMIN", "DOCTOR", "ASSISTANT", "ALL_ROLES",
    "READ_CLINICAL", "WRITE_CLINICAL", "APPROVE_CLINICAL",
    "MANAGE_USERS", "VIEW_SECURITY_LOG", "MANAGE_DATA_RIGHTS", "MANAGE_MODELS",
    "has_permission", "is_valid_role", "permissions_for",
]
