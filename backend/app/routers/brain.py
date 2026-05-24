"""API para o cérebro Hermes (gateway em ~/.hermes) controlar dispositivos pareados."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.command_wait import format_command_result_message, wait_for_command
from app.db import get_db
from app.memory.service import get_recent_thread, record_thread_event
from app.deps import get_brain_or_admin, require_brain_service_key
from app.google_natural import RoutedGoogleAction, route_google_natural
from app.google_workspace import GoogleWorkspaceError, is_destructive, run as run_google_workspace
from app.audit_service import safe_metadata, write_audit
from app.models import Command, ConversationThread, Device, User
from app.routers.commands import create_command, create_natural_command
from app.schemas import (
    BrainCommandRequest,
    BrainGoogleRequest,
    BrainGoogleResponse,
    BrainContextResponse,
    BrainCommandResponse,
    BrainRawCommandRequest,
    CreateCommandRequest,
    DeviceSummary,
    ConversationThreadEntry,
    NaturalCommandRequest,
)

router = APIRouter(prefix="/brain", tags=["brain"])


def _google_confirmation_prompt(action: RoutedGoogleAction) -> str:
    return f"Confirme a ação Google {action.service}.{action.action} com estes parâmetros: {action.params}"


@router.post("/google", response_model=BrainGoogleResponse)
def brain_google(
    body: BrainGoogleRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(get_brain_or_admin),
) -> BrainGoogleResponse:
    try:
        action = route_google_natural(body.text)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    thread = get_recent_thread(db, "user", str(actor.id))
    if thread is None:
        thread = ConversationThread(actor_type="user", actor_id=str(actor.id), origin_channel="brain", subject=body.text[:60])
        db.add(thread)
        db.flush()

    if action.confirmation_required and not body.confirm:
        record_thread_event(
            db,
            thread,
            kind="google_confirmation_required",
            payload={
                "service": action.service,
                "action": action.action,
                "params": action.params,
            },
            summary=_google_confirmation_prompt(action),
        )
        write_audit(
            db,
            actor_type="user",
            actor_id=str(actor.id),
            action="google_confirmation_required",
            metadata=safe_metadata(
                {
                    "service": action.service,
                    "action": action.action,
                    "params": action.params,
                    "summary": _google_confirmation_prompt(action),
                }
            ),
        )
        db.commit()
        return BrainGoogleResponse(
            thread_id=thread.id,
            service=action.service,
            action=action.action,
            status="needs_confirmation",
            message=_google_confirmation_prompt(action),
            requires_confirmation=True,
            summary=_google_confirmation_prompt(action),
            data=None,
        )

    try:
        result = run_google_workspace(action.service, action.action, action.params, confirm=body.confirm)
    except GoogleWorkspaceError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    write_audit(
        db,
        actor_type="user",
        actor_id=str(actor.id),
        action="google_workspace_action",
        metadata=safe_metadata(
            {
                "service": action.service,
                "action": action.action,
                "confirm": body.confirm,
                "destructive": is_destructive(action.service, action.action),
                "summary": result.summary,
            }
        ),
    )
    record_thread_event(
        db,
        thread,
        kind="google_workspace_action",
        payload={
            "service": action.service,
            "action": action.action,
            "confirm": body.confirm,
            "summary": result.summary,
        },
        summary=result.summary,
    )
    db.commit()
    return BrainGoogleResponse(
        thread_id=thread.id,
        service=action.service,
        action=action.action,
        status="done",
        message=result.summary or f"Executed {action.service}.{action.action}",
        requires_confirmation=False,
        summary=result.summary,
        data=result.data if isinstance(result.data, (dict, list)) else None,
        raw_output=result.raw_output,
    )


@router.get("/status")
def brain_status(_: None = Depends(require_brain_service_key)) -> dict:
    return {"status": "ok", "role": "hermes-brain-bridge"}


@router.get("/devices")
def brain_list_devices(
    db: Session = Depends(get_db),
    _: None = Depends(require_brain_service_key),
    limit: int = 50,
) -> dict:
    limit = min(max(limit, 1), 100)
    q = (
        select(Device)
        .where(Device.revoked_at.is_(None))
        .order_by(Device.name.asc())
        .limit(limit)
    )
    items = db.scalars(q).all()
    return {
        "items": [
            DeviceSummary.model_validate(
                {
                    "id": d.id,
                    "name": d.name,
                    "platform": d.platform,
                    "last_seen": d.last_seen,
                    "revoked_at": d.revoked_at,
                }
            )
            for d in items
        ],
        "total": len(items),
    }


@router.post("/command", response_model=BrainCommandResponse, status_code=status.HTTP_201_CREATED)
def brain_dispatch_command(
    body: BrainCommandRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(get_brain_or_admin),
) -> BrainCommandResponse:
    """
    O cérebro Hermes envia texto livre; a API resolve dispositivo + tipo de comando.
    Usar header X-Hermes-Brain-Key (gateway) ou JWT admin (painel/app).
    """
    try:
        result = create_natural_command(
            NaturalCommandRequest(
                text=body.text,
                device_id=body.device_id,
                thread_id=body.thread_id,
                notify_channel=body.notify_channel or "silent",
                notify_on=body.notify_on or "done",
            ),
            db,
            actor,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    cmd = db.get(Command, result.command.id)
    if cmd is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Comando não encontrado após criação")

    if body.wait_timeout_seconds > 0:
        cmd = wait_for_command(db, cmd.id, timeout_seconds=body.wait_timeout_seconds)

    message = format_command_result_message(
        device_name=result.parsed_device_name,
        command_type=result.parsed_type,
        status=cmd.status,
        result=cmd.result,
        logs=cmd.logs,
    )
    return BrainCommandResponse(
        command_id=cmd.id,
        device_name=result.parsed_device_name,
        command_type=result.parsed_type,
        status=cmd.status,
        message=message,
        result=cmd.result,
        thread_id=result.thread_id,
    )


@router.get("/commands/{command_id}", response_model=BrainCommandResponse)
def brain_get_command(
    command_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: None = Depends(require_brain_service_key),
) -> BrainCommandResponse:
    cmd = db.get(Command, command_id)
    if cmd is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Comando não encontrado")
    device = db.get(Device, cmd.device_id)
    device_name = device.name if device else "?"
    message = format_command_result_message(
        device_name=device_name,
        command_type=cmd.type,
        status=cmd.status,
        result=cmd.result,
        logs=cmd.logs,
    )
    return BrainCommandResponse(
        command_id=cmd.id,
        device_name=device_name,
        command_type=cmd.type,
        status=cmd.status,
        message=message,
        result=cmd.result,
        thread_id=cmd.thread_id,
    )


@router.post("/command/raw", status_code=status.HTTP_201_CREATED)
def brain_dispatch_raw(
    body: BrainRawCommandRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(get_brain_or_admin),
) -> dict:
    """Comando explícito por nome do dispositivo (ex.: server_docker_ps no VPS-Brain)."""
    device = (
        db.query(Device)
        .filter(Device.name.ilike(body.device_name.strip()), Device.revoked_at.is_(None))
        .first()
    )
    if device is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Dispositivo não encontrado: {body.device_name}")
    req = CreateCommandRequest(type=body.command_type, payload=body.payload, notify_channel="silent")
    cmd = create_command(device.id, req, db, actor)
    return {
        "command_id": str(cmd.id),
        "device_name": device.name,
        "command_type": cmd.type,
        "status": cmd.status,
        "thread_id": str(cmd.thread_id) if cmd.thread_id else None,
    }


@router.get("/context", response_model=BrainContextResponse)
def brain_context(
    db: Session = Depends(get_db),
    _: None = Depends(require_brain_service_key),
    actor_type: str = "user",
    actor_id: str | None = None,
    thread_id: uuid.UUID | None = None,
) -> BrainContextResponse:
    thread = db.get(ConversationThread, thread_id) if thread_id is not None else get_recent_thread(db, actor_type, actor_id)
    recent_threads = (
        db.query(ConversationThread)
        .filter(ConversationThread.actor_type == actor_type)
        .order_by(ConversationThread.updated_at.desc(), ConversationThread.created_at.desc())
        .limit(5)
        .all()
    )
    return BrainContextResponse(
        thread=ConversationThreadEntry.model_validate(thread) if thread is not None else None,
        recent_threads=[ConversationThreadEntry.model_validate(t) for t in recent_threads],
    )
