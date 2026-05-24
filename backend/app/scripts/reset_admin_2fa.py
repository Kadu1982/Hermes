"""Reset admin password + TOTP (new Google Authenticator QR)."""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.db import SessionLocal  # noqa: E402
from app.models import User  # noqa: E402
from app.security import build_totp_uri, generate_totp_secret, hash_password  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description="Reset Hermes admin 2FA (and optional password)")
    p.add_argument("--email", default=os.environ.get("HERMES_ADMIN_EMAIL", "admin@example.com"))
    p.add_argument("--password", default=os.environ.get("HERMES_ADMIN_PASSWORD"))
    args = p.parse_args()

    db = SessionLocal()
    try:
        email = args.email.lower().strip()
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            print("ERROR: user not found:", email)
            sys.exit(1)
        secret = generate_totp_secret()
        user.totp_secret = secret
        user.totp_confirmed = True
        if args.password:
            user.password_hash = hash_password(args.password)
            print("Password updated from HERMES_ADMIN_PASSWORD")
        db.commit()
        uri = build_totp_uri(secret, email)
        print("OK: 2FA reset for", email)
        print("TOTP URI:", uri)
        print("Scan in Google Authenticator (remove old Hermes entries first).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
