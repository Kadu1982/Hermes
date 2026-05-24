from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog


def write_audit(
    db: Session,
    *,
    actor_type: str,
    actor_id: str | None,
    action: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    row = AuditLog(
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        metadata_=metadata,
    )
    db.add(row)


def safe_metadata(meta: dict[str, Any] | None) -> dict[str, Any] | None:
    if meta is None:
        return None
    try:
        return json.loads(json.dumps(meta, default=str))
    except (TypeError, ValueError):
        return {"_error": "unserializable_metadata"}
