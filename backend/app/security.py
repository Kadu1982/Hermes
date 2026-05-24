from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import HTTPException, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Device, User

settings = get_settings()
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
ph = PasswordHasher()

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def hash_pairing_code(raw_code: str, pepper: str | None = None) -> str:
    pepper = pepper or settings.pairing_pepper
    return ph.hash(f"{pepper}:{raw_code.strip().upper()}")


def verify_pairing_code(raw_code: str, code_hash: str, pepper: str | None = None) -> bool:
    pepper = pepper or settings.pairing_pepper
    try:
        ph.verify(code_hash, f"{pepper}:{raw_code.strip().upper()}")
        return True
    except VerifyMismatchError:
        return False


def hash_device_secret(secret: str) -> str:
    return pwd_context.hash(secret)


def verify_device_secret(secret: str, token_hash: str) -> bool:
    return pwd_context.verify(secret, token_hash)


def create_access_token(
    subject: str,
    *,
    token_type: str = "admin",
    tfa_verified: bool = False,
    expires_delta: timedelta | None = None,
) -> str:
    expire = datetime.now(tz=UTC) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "typ": token_type,
        "tfa": tfa_verified,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def build_totp_uri(secret: str, email: str) -> str:
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name="Hermes")


def verify_totp(secret: str, code: str) -> bool:
    totp = pyotp.TOTP(secret)
    # valid_window=2 → ±60s (relógio do telemóvel ligeiramente desajustado)
    return totp.verify(code.strip().replace(" ", ""), valid_window=2)


def parse_device_token(raw: str) -> tuple[uuid.UUID, str]:
    parts = raw.strip().split(".", 2)
    if len(parts) != 3 or parts[0] != "hermes":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid device token format")
    try:
        device_id = uuid.UUID(parts[1])
    except ValueError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid device id") from exc
    secret = parts[2]
    if len(secret) < 16:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid device token")
    return device_id, secret


def authenticate_device(db: Session, raw_token: str) -> Device:
    device_id, secret = parse_device_token(raw_token)
    device = db.get(Device, device_id)
    if device is None or device.revoked_at is not None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Device not authorized")
    if not verify_device_secret(secret, device.token_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Device not authorized")
    return device


def new_device_token(device_id: uuid.UUID) -> tuple[str, str]:
    secret = secrets.token_urlsafe(32)
    token = f"hermes.{device_id}.{secret}"
    return token, secret


def authenticate_admin_partial(db: Session, email: str, password: str) -> User:
    user = db.query(User).filter(User.email == email.lower().strip()).first()
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    return user
