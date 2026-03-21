from __future__ import annotations

import argparse
from typing import Sequence

from . import create_app
from .models import User, db


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.admin_cli",
        description="Administrative commands for YeaBook user management.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser(
        "list-users",
        help="List all WebUI users stored in the database.",
    )

    reset_parser = subparsers.add_parser(
        "reset-password",
        help="Reset the password of an existing WebUI user.",
    )
    reset_parser.add_argument("username", help="Username of the WebUI account.")
    reset_parser.add_argument("password", help="New password to store.")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    app = create_app()
    try:
        with app.app_context():
            if args.command == "list-users":
                return _list_users()
            if args.command == "reset-password":
                return _reset_password(args.username, args.password)
    finally:
        with app.app_context():
            db.session.remove()
            db.engine.dispose()

    parser.error("Unknown command.")
    return 2


def _list_users() -> int:
    users = User.query.order_by(User.username.asc()).all()
    if not users:
        print("No WebUI users found.")
        return 0

    print("ID\tUsername\tRole\tCreated")
    for user in users:
        role = "admin" if user.is_admin else "user"
        created = user.created_at.isoformat() if user.created_at else "-"
        print(f"{user.id}\t{user.username}\t{role}\t{created}")
    return 0


def _reset_password(username: str, password: str) -> int:
    user = User.query.filter_by(username=username).first()
    if not user:
        print(f"User '{username}' not found.")
        return 1

    user.set_password(password)
    db.session.commit()
    print(f"Password updated for user '{username}'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
