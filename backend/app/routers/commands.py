from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit_service import safe_metadata, write_audit
from app.db import get_db
from app.deps import get_brain_or_admin, get_current_actor, get_current_admin, get_current_device
from app.memory.service import get_or_create_thread, record_command_completed, record_command_created
from app.models import ALLOWED_COMMAND_TYPES, Command, ConversationThread, Device, User
from app.natural_commands import parse_natural_command
from app.notify_service import notify_command_finished
from app.schemas import (
    CommandCompleteRequest,
    CommandJob,
    CommandJobAdmin,
    CreateCommandRequest,
    NaturalCommandRequest,
    NaturalCommandResponse,
)

router = APIRouter(tags=["commands"])


def _validate_payload(cmd_type: str, payload: dict | None) -> None:
    payload = payload or {}
    if cmd_type in ("ping", "revoke_local", "noop", "get_location") and payload:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Payload must be empty for this command type")
    if cmd_type == "speak":
        if not payload or not str(payload.get("text", "")).strip():
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "speak requires payload.text")
    if cmd_type == "request_download":
        if not payload.get("file_id"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "request_download requires file_id")
    if cmd_type == "navigate_to":
        destination = str(payload.get("destination", "")).strip()
        if not destination:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "navigate_to requires destination")
        if payload.keys() - {"destination", "mode"}:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "navigate_to only accepts destination and mode")
        mode = str(payload.get("mode", "driving")).strip().lower()
        if mode not in {"driving", "walking", "bicycling", "transit"}:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "navigate_to.mode must be driving, walking, bicycling or transit")
    if cmd_type == "take_photo":
        if set(payload.keys()) - {"archive_only"}:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "take_photo only accepts archive_only")
        if payload and "archive_only" in payload and not isinstance(payload["archive_only"], bool):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "take_photo.archive_only must be boolean")


@router.post("/devices/{device_id}/commands", response_model=CommandJobAdmin, status_code=status.HTTP_201_CREATED)
def create_command(
    device_id: uuid.UUID,
    body: CreateCommandRequest,
    db: Session = Depends(get_db),
    actor: User | Device = Depends(get_current_actor),
) -> CommandJobAdmin:
    device = db.get(Device, device_id)
    if device is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Device not found")
    if device.revoked_at is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Device revoked")
    if body.type not in ALLOWED_COMMAND_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unsupported command type")
    _validate_payload(body.type, body.payload)
    thread: ConversationThread | None = None
    if body.thread_id is not None:
        thread = db.get(ConversationThread, body.thread_id)
        if thread is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Thread not found")
    else:
        actor_type = "user" if isinstance(actor, User) else "device"
        thread = get_or_create_thread(
            db,
            actor_type=actor_type,
            actor_id=str(actor.id),
            origin_channel="api",
            subject=body.source_text or body.type,
        )
    cmd = Command(
        device_id=device.id,
        type=body.type,
        payload=body.payload,
        status="pending",
        thread_id=thread.id if thread is not None else None,
        created_by_user_id=actor.id if isinstance(actor, User) else None,
        created_by_device_id=actor.id if isinstance(actor, Device) else None,
        notify_channel=body.notify_channel,
        notify_on=body.notify_on,
        source_text=body.source_text,
    )
    db.add(cmd)
    db.flush()
    if thread is not None:
        record_command_created(
            db,
            thread=thread,
            command=cmd,
            intent=cmd.type,
            target_device=device,
            source_text=body.source_text,
        )
    write_audit(
        db,
        actor_type="user" if isinstance(actor, User) else "device",
        actor_id=str(actor.id),
        action="command_created",
        metadata=safe_metadata({"command_id": str(cmd.id), "device_id": str(device.id), "type": cmd.type}),
    )
    db.commit()
    db.refresh(cmd)
    return CommandJobAdmin(
        id=cmd.id,
        type=cmd.type,
        payload=cmd.payload,
        status=cmd.status,
        result=cmd.result,
        created_at=cmd.created_at,
        completed_at=cmd.completed_at,
        created_by_user_id=cmd.created_by_user_id,
        created_by_device_id=cmd.created_by_device_id,
        notify_channel=cmd.notify_channel,
        notify_on=cmd.notify_on,
        source_text=cmd.source_text,
        thread_id=cmd.thread_id,
    )


@router.post("/commands/natural", response_model=NaturalCommandResponse, status_code=status.HTTP_201_CREATED)
def create_natural_command(
    body: NaturalCommandRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_brain_or_admin),
) -> NaturalCommandResponse:
    try:
        from app.routing.service import route_natural_command

        routed = route_natural_command(
            db,
            body.text,
            actor_type="user",
            actor_id=str(admin.id),
            explicit_device_id=body.device_id,
            thread_id=body.thread_id,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    create_body = CreateCommandRequest(
        type=routed.intent,
        payload=routed.payload,
        notify_channel=body.notify_channel,
        notify_on=body.notify_on,
        source_text=body.text,
        thread_id=routed.thread.id,
    )
    cmd_resp = create_command(routed.device.id, create_body, db, admin)
    return NaturalCommandResponse(
        command=cmd_resp,
        parsed_device_name=routed.device.name,
        parsed_type=routed.intent,
        confidence=routed.confidence,
        thread_id=routed.thread.id,
    )


@router.get("/devices/{device_id}/commands")
def list_commands(
    device_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
    limit: int = 50,
    offset: int = 0,
) -> dict:
    if db.get(Device, device_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Device not found")
    limit = min(max(limit, 1), 100)
    offset = max(offset, 0)
    q = (
        select(Command)
        .where(Command.device_id == device_id)
        .order_by(Command.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    items = db.scalars(q).all()
    total = db.scalar(
        select(func.count()).select_from(Command).where(Command.device_id == device_id)
    ) or 0
    return {
        "items": [
            CommandJobAdmin(
                id=c.id,
                type=c.type,
                payload=c.payload,
                status=c.status,
                result=c.result,
                created_at=c.created_at,
                completed_at=c.completed_at,
                created_by_user_id=c.created_by_user_id,
                created_by_device_id=c.created_by_device_id,
                notify_channel=c.notify_channel,
                notify_on=c.notify_on,
                source_text=c.source_text,
                thread_id=c.thread_id,
            )
            for c in items
        ],
        "total": total,
    }


@router.get("/devices/me/commands/next", response_model=CommandJob | None)
def next_command(
    db: Session = Depends(get_db),
    device: Device = Depends(get_current_device),
) -> CommandJob | Response:
    stmt = (
        select(Command)
        .where(Command.device_id == device.id, Command.status == "pending")
        .order_by(Command.created_at.asc())
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    cmd = db.execute(stmt).scalar_one_or_none()
    if cmd is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    cmd.status = "running"
    cmd.claimed_at = datetime.now(tz=UTC)
    db.commit()
    db.refresh(cmd)
    return CommandJob(id=cmd.id, type=cmd.type, payload=cmd.payload, status=cmd.status)


@router.post("/devices/me/commands/{command_id}/complete", status_code=status.HTTP_204_NO_CONTENT)
def complete_command(
    command_id: uuid.UUID,
    body: CommandCompleteRequest,
    db: Session = Depends(get_db),
    device: Device = Depends(get_current_device),
) -> Response:
    cmd = db.get(Command, command_id)
    if cmd is None or cmd.device_id != device.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Command not found")
    if cmd.status != "running":
        raise HTTPException(status.HTTP_409_CONFLICT, "Command not in running state")
    cmd.status = "done" if body.status == "done" else "failed"
    cmd.result = body.result
    cmd.logs = body.logs
    cmd.completed_at = datetime.now(tz=UTC)
    if cmd.thread_id is not None:
        thread = db.get(ConversationThread, cmd.thread_id)
        if thread is not None:
            record_command_completed(
                db,
                thread=thread,
                command=cmd,
                status=cmd.status,
                result=body.result,
                logs=body.logs,
            )
    write_audit(
        db,
        actor_type="device",
        actor_id=str(device.id),
        action="command_completed",
        metadata=safe_metadata({"command_id": str(cmd.id), "status": cmd.status}),
    )
    notify_command_finished(db, cmd, device)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
