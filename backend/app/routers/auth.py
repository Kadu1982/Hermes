from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.audit_service import safe_metadata, write_audit
from app.db import get_db
from app.deps import get_current_admin
from app.models import User
from app.schemas import (
    AdminLoginRequest,
    AdminLoginResponse,
    TokenResponse,
    TwoFactorVerifyRequest,
)
from app.rate_limit import limiter
from app.security import (
    create_access_token,
    decode_token,
    verify_totp,
    authenticate_admin_partial,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=AdminLoginResponse)
@limiter.limit("30/minute")
def login(body: AdminLoginRequest, request: Request, db: Session = Depends(get_db)) -> AdminLoginResponse:
    user = authenticate_admin_partial(db, body.email, body.password)
    tfa_ok = bool(user.totp_secret)
    token = create_access_token(
        str(user.id),
        tfa_verified=False,
    )
    write_audit(
        db,
        actor_type="user",
        actor_id=str(user.id),
        action="admin_login",
        metadata=safe_metadata({"email": user.email, "step": "password"}),
    )
    db.commit()
    return AdminLoginResponse(access_token=token, requires_2fa=tfa_ok)


@router.post("/2fa/verify", response_model=TokenResponse)
def verify_2fa(body: TwoFactorVerifyRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        payload = decode_token(body.access_token)
    except Exception as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token") from exc
    if payload.get("typ") != "admin" or payload.get("tfa"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token state")
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid subject")
    user = db.get(User, uuid.UUID(str(sub)))
    if user is None or not user.totp_secret:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "2FA not configured")
    if not verify_totp(user.totp_secret, body.code.strip()):
        write_audit(
            db,
            actor_type="user",
            actor_id=str(user.id),
            action="admin_2fa_failed",
            metadata=None,
        )
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid 2FA code")
    full = create_access_token(str(user.id), tfa_verified=True)
    write_audit(
        db,
        actor_type="user",
        actor_id=str(user.id),
        action="admin_2fa_ok",
        metadata=None,
    )
    db.commit()
    return TokenResponse(access_token=full)


@router.get("/session")
def auth_session(admin: User = Depends(get_current_admin)) -> dict:
    """Valida JWT completo (2FA feito). App Android usa para confirmar sessão."""
    return {"ok": True, "email": admin.email, "tfa": True}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    _: User = Depends(get_current_admin),
) -> None:
    # Stateless JWT — client drops token
    return None
