"""First-run account creation (security phase, C.1).

    python -m backend.security.bootstrap --username drpawal --role admin

Deliberately a CLI rather than a seeded default account. Shipping a known
admin/admin is how most self-hosted clinical tools end up compromised: the
default survives into production because nothing forces anyone to change it.
Here no account exists until a human creates one at a terminal, so there is no
default to leak.

The password is read from a prompt (not echoed) or from ``PCW_BOOTSTRAP_PASSWORD``
for automated setup. It is never accepted as a command-line argument -- argv is
visible to other processes and lands in shell history.
"""
from __future__ import annotations

import argparse
import getpass
import os
import sys

from sqlalchemy import func, select

from backend.db import init_db, session_scope
from backend.models import User
from backend.security import roles
from backend.security.passwords import PasswordError, hash_password
from backend.security.sessions import record_security_event


def user_count() -> int:
    with session_scope() as db:
        return db.execute(select(func.count()).select_from(User)).scalar_one()


def create_user(username: str, password: str, role: str,
                full_name: str | None = None, *, must_change: bool = False) -> None:
    if not roles.is_valid_role(role):
        raise SystemExit(f"role must be one of {', '.join(roles.ALL_ROLES)}")
    username = username.strip()
    if not username:
        raise SystemExit("username cannot be empty")

    with session_scope() as db:
        existing = db.execute(
            select(User).where(User.username == username)
        ).scalar_one_or_none()
        if existing is not None:
            raise SystemExit(f"user {username!r} already exists")
        try:
            pw_hash = hash_password(password)
        except PasswordError as exc:
            raise SystemExit(str(exc)) from exc

        db.add(User(username=username, full_name=full_name, password_hash=pw_hash,
                    role=role, must_change_password=must_change))
        record_security_event(db, event_type="user_created", username=username,
                              detail=f"bootstrap CLI created {username} ({role})")
    print(f"created {username!r} with role {role}")


def _read_password() -> str:
    env = os.environ.get("PCW_BOOTSTRAP_PASSWORD")
    if env:
        return env
    if not sys.stdin.isatty():
        raise SystemExit(
            "no TTY for a password prompt. Set PCW_BOOTSTRAP_PASSWORD instead "
            "(never pass a password as a command-line argument -- argv is visible "
            "to other processes and is recorded in shell history)."
        )
    first = getpass.getpass("Password: ")
    second = getpass.getpass("Repeat: ")
    if first != second:
        raise SystemExit("passwords did not match")
    return first


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an application user.")
    parser.add_argument("--username", required=True)
    parser.add_argument("--role", default=roles.ADMIN,
                        help=f"one of: {', '.join(roles.ALL_ROLES)} (default: admin)")
    parser.add_argument("--full-name", default=None)
    parser.add_argument("--must-change-password", action="store_true",
                        help="force a password change at first login")
    args = parser.parse_args()

    init_db()
    create_user(args.username, _read_password(), args.role, args.full_name,
                must_change=args.must_change_password)

    if user_count() == 1:
        print(
            "\nThis is the only account. An 'admin' can manage users but "
            "deliberately CANNOT approve clinical results -- create a 'doctor' "
            "account for the treating clinician:\n"
            "  python -m backend.security.bootstrap --username <name> --role doctor"
        )


if __name__ == "__main__":  # pragma: no cover
    main()
