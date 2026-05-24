from __future__ import annotations

import argparse
import os
import sys
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.db import SessionLocal  # noqa: E402
from app.models import User  # noqa: E402
from app.security import generate_totp_secret, build_totp_uri, hash_password  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description="Bootstrap Hermes admin user")
    p.add_argument("--email", default=os.environ.get("HERMES_ADMIN_EMAIL", "admin@example.com"))
    p.add_argument("--password", default=os.environ.get("HERMES_ADMIN_PASSWORD", "change-me-now"))
    args = p.parse_args()

    db = SessionLocal()
    try:
        email = args.email.lower().strip()
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print("User already exists:", email)
            return
        secret = generate_totp_secret()
        user = User(
            id=uuid.uuid4(),
            email=email,
            password_hash=hash_password(args.password),
            totp_secret=secret,
            totp_confirmed=True,
        )
        db.add(user)
        db.commit()
        print("Created admin:", email)
        print("TOTP URI (store securely):", build_totp_uri(secret, email))
    finally:
        db.close()


if __name__ == "__main__":
    main()
