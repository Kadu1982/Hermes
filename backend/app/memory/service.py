from __future__ import annotations

from datetime import UTC, datetime
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Command, ConversationThread, Device, MemoryEvent


def get_recent_thread(db: Session, actor_type: str, actor_id: str | None) -> ConversationThread | None:
    stmt = (
        select(ConversationThread)
        .where(ConversationThread.actor_type == actor_type)
        .order_by(ConversationThread.updated_at.desc(), ConversationThread.created_at.desc())
        .limit(1)
    )
    if actor_id is None:
        stmt = stmt.where(ConversationThread.actor_id.is_(None))
    else:
        stmt = stmt.where(ConversationThread.actor_id == actor_id)
    return db.execute(stmt).scalar_one_or_none()


def get_or_create_thread(
    db: Session,
    *,
    actor_type: str,
    actor_id: str | None,
    origin_channel: str | None = None,
    subject: str | None = None,
    force_new: bool = False,
) -> ConversationThread:
    if not force_new:
        recent = get_recent_thread(db, actor_type, actor_id)
        if recent is not None:
            return recent
    thread = ConversationThread(
        actor_type=actor_type,
        actor_id=actor_id,
        origin_channel=origin_channel,
        subject=subject,
        summary=subject,
    )
    db.add(thread)
    db.flush()
    return thread


def _touch_thread(
    thread: ConversationThread,
    *,
    intent: str | None = None,
    target_device_id: uuid.UUID | None = None,
    command_id: uuid.UUID | None = None,
    summary: str | None = None,
) -> None:
    if intent is not None:
        thread.last_intent = intent
    if target_device_id is not None:
        thread.last_target_device_id = target_device_id
    if command_id is not None:
        thread.last_command_id = command_id
    if summary is not None:
        thread.summary = summary


def record_thread_event(
    db: Session,
    thread: ConversationThread,
    *,
    kind: str,
    payload: dict[str, Any] | None = None,
    command_id: uuid.UUID | None = None,
    intent: str | None = None,
    target_device_id: uuid.UUID | None = None,
    summary: str | None = None,
) -> MemoryEvent:
    _touch_thread(
        thread,
        intent=intent,
        target_device_id=target_device_id,
        command_id=command_id,
        summary=summary,
    )
    event = MemoryEvent(
        thread_id=thread.id,
        command_id=command_id,
        kind=kind,
        payload=payload,
    )
    db.add(event)
    db.add(thread)
    thread.updated_at = datetime.now(tz=UTC)
    db.flush()
    return event


def record_command_created(
    db: Session,
    *,
    thread: ConversationThread,
    command: Command,
    intent: str,
    target_device: Device,
    source_text: str | None,
    confidence: str | None = None,
) -> None:
    summary = f"{intent} -> {target_device.name}"
    record_thread_event(
        db,
        thread,
        kind="command_created",
        command_id=command.id,
        intent=intent,
        target_device_id=target_device.id,
        summary=summary,
        payload={
            "command_id": str(command.id),
            "intent": intent,
            "target_device_id": str(target_device.id),
            "target_device_name": target_device.name,
            "source_text": source_text,
            "confidence": confidence,
        },
    )


def record_command_completed(
    db: Session,
    *,
    thread: ConversationThread,
    command: Command,
    status: str,
    result: dict[str, Any] | None,
    logs: str | None,
) -> None:
    summary = f"{command.type} {status}"
    record_thread_event(
        db,
        thread,
        kind="command_completed",
        command_id=command.id,
        summary=summary,
        payload={
            "command_id": str(command.id),
            "status": status,
            "result": result,
            "logs_present": bool(logs),
        },
    )
