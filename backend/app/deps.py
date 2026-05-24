from __future__ import annotations

import secrets
import uuid
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import Device, User
from app.security import authenticate_device, decode_token

bearer = HTTPBearer(auto_error=False)


def get_current_admin_partial(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    try:
        payload = decode_token(creds.credentials)
    except JWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token") from exc
    if payload.get("typ") != "admin":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token type")
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid subject")
    user = db.get(User, uuid.UUID(str(sub)))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user


def get_current_admin(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    user = get_current_admin_partial(creds, db)
    try:
        payload = decode_token(creds.credentials)  # type: ignore[union-attr]
    except JWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token") from exc
    if not payload.get("tfa"):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Confirme o código 2FA no login (sessão incompleta).",
        )
    return user


def get_brain_service_user(db: Session) -> User:
    """Utilizador admin usado quando o cérebro Hermes (gateway) chama a API."""
    user = db.query(User).filter(User.email == "admin@example.com").first()
    if user is None:
        user = db.query(User).order_by(User.created_at.asc()).first()
    if user is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Admin user not configured")
    return user


def get_brain_or_admin(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: Annotated[Session, Depends(get_db)],
    x_hermes_brain_key: Annotated[str | None, Header(alias="X-Hermes-Brain-Key")] = None,
) -> User:
    """
    Autenticação para o cérebro Hermes na VPS (chave de serviço) ou admin JWT (app/painel).
  A chave de serviço dispensa 2FA — só corre em localhost/VPS.
    """
    settings = get_settings()
    if (
        settings.brain_service_key
        and x_hermes_brain_key
        and secrets.compare_digest(x_hermes_brain_key, settings.brain_service_key)
    ):
        return get_brain_service_user(db)
    return get_current_admin(creds, db)


def require_brain_service_key(
    x_hermes_brain_key: Annotated[str | None, Header(alias="X-Hermes-Brain-Key")] = None,
) -> None:
    settings = get_settings()
    if not settings.brain_service_key or not x_hermes_brain_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "X-Hermes-Brain-Key required")
    if not secrets.compare_digest(x_hermes_brain_key, settings.brain_service_key):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid brain service key")


def get_current_device(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: Annotated[Session, Depends(get_db)],
):
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    return authenticate_device(db, creds.credentials)


def get_current_actor(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> User | Device:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    if creds.credentials.startswith("hermes."):
        return authenticate_device(db, creds.credentials)
    try:
        payload = decode_token(creds.credentials)
    except JWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token") from exc
    if payload.get("typ") != "admin":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token type")
    if not payload.get("tfa"):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Confirme o código 2FA no login (sessão incompleta).",
        )
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid subject")
    user = db.get(User, uuid.UUID(str(sub)))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user
