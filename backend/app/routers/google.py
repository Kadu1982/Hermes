from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.audit_service import safe_metadata, write_audit
from app.db import get_db
from app.deps import get_brain_or_admin
from app.google_workspace import GoogleWorkspaceError, auth_check, is_destructive, run
from app.models import User

router = APIRouter(prefix="/integrations/google", tags=["google"])


class GoogleWorkspaceActionRequest(BaseModel):
    params: dict[str, Any] = Field(default_factory=dict)
    confirm: bool = False


class GoogleWorkspaceActionResponse(BaseModel):
    service: str
    action: str
    ok: bool
    summary: str | None = None
    data: Any | None = None
    raw_output: str | None = None


@router.get("/status")
def google_status(_: User = Depends(get_brain_or_admin)) -> dict[str, Any]:
    return {
        "authenticated": auth_check(),
        "status": "ok",
        "provider": "google-workspace",
    }


@router.post("/{service}/{action}", response_model=GoogleWorkspaceActionResponse)
def google_action(
    service: str,
    action: str,
    body: GoogleWorkspaceActionRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(get_brain_or_admin),
) -> GoogleWorkspaceActionResponse:
    try:
        result = run(service, action, body.params, confirm=body.confirm)
    except GoogleWorkspaceError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    write_audit(
        db,
        actor_type="user",
        actor_id=str(actor.id),
        action="google_workspace_action",
        metadata=safe_metadata(
            {
                "service": service,
                "action": action,
                "confirm": body.confirm,
                "destructive": is_destructive(service, action),
                "summary": result.summary,
            }
        ),
    )
    db.commit()

    return GoogleWorkspaceActionResponse(
        service=service,
        action=action,
        ok=True,
        summary=result.summary,
        data=result.data,
        raw_output=result.raw_output,
    )
