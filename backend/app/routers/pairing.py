from __future__ import annotations

import secrets
import string
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.audit_service import safe_metadata, write_audit
from app.db import get_db
from app.deps import get_current_admin
from app.models import PairingCode, User
from app.schemas import (
    CreatePairingCodeRequest,
    CreatePairingCodeResponse,
)
from app.security import hash_pairing_code

router = APIRouter(prefix="/pairing", tags=["pairing"])

CODE_ALPHABET = string.ascii_uppercase + string.digits
CODE_ALPHABET = "".join(c for c in CODE_ALPHABET if c not in "0O1IL")


@router.post("/codes", response_model=CreatePairingCodeResponse, status_code=status.HTTP_201_CREATED)
def create_pairing_code(
    body: CreatePairingCodeRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> CreatePairingCodeResponse:
    raw = "".join(secrets.choice(CODE_ALPHABET) for _ in range(8))
    expires = datetime.now(tz=UTC) + timedelta(minutes=10)
    row = PairingCode(
        code_hash=hash_pairing_code(raw),
        label=body.label,
        expires_at=expires,
        created_by_user_id=admin.id,
    )
    db.add(row)
    db.flush()
    write_audit(
        db,
        actor_type="user",
        actor_id=str(admin.id),
        action="pairing_code_created",
        metadata=safe_metadata({"pairing_code_id": str(row.id)}),
    )
    db.commit()
    db.refresh(row)
    return CreatePairingCodeResponse(id=row.id, code=raw, expires_at=row.expires_at)
