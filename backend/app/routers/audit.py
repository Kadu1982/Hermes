from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_admin
from app.models import AuditLog, User
from app.schemas import AuditLogEntry

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
def list_audit(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
    device_id: uuid.UUID | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict:
    _ = admin
    limit = min(max(limit, 1), 500)
    offset = max(offset, 0)
    q = select(AuditLog).order_by(AuditLog.created_at.desc())
    if device_id is not None:
        q = q.where(AuditLog.actor_id == str(device_id))
    q = q.offset(offset).limit(limit)
    items = db.scalars(q).all()
    total = db.scalar(select(func.count()).select_from(AuditLog)) or 0
    return {
        "items": [
            AuditLogEntry(
                id=r.id,
                actor_type=r.actor_type,
                actor_id=r.actor_id,
                action=r.action,
                metadata=r.metadata_,
                created_at=r.created_at,
            )
            for r in items
        ],
        "total": total,
    }
