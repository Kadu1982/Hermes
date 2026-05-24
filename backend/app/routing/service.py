from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.memory.service import get_or_create_thread, get_recent_thread, record_thread_event
from app.models import Command, ConversationThread, Device
from app.natural_commands import parse_natural_command, resolve_device

_CONTINUATION_HINT = re.compile(
    r"\b(continua|continue|de novo|repete|repetir|again|faz isso|o mesmo|isso|aquilo)\b",
    re.I,
)


@dataclass
class RoutedCommand:
    thread: ConversationThread
    device: Device
    intent: str
    payload: dict | None
    confidence: str
    thread_reused: bool


def _is_continuation(text: str) -> bool:
    return bool(_CONTINUATION_HINT.search(text))


def _active_device_from_context(db: Session, thread: ConversationThread | None) -> Device | None:
    if thread is None or thread.last_target_device_id is None:
        return None
    device = db.get(Device, thread.last_target_device_id)
    if device is None or device.revoked_at is not None:
        return None
    return device


def _reuse_last_command(db: Session, thread: ConversationThread | None) -> tuple[str, dict | None] | None:
    if thread is None or thread.last_command_id is None:
        return None
    cmd = db.get(Command, thread.last_command_id)
    if cmd is None:
        return None
    return cmd.type, cmd.payload


def route_natural_command(
    db: Session,
    text: str,
    *,
    actor_type: str,
    actor_id: str | None,
    explicit_device_id: uuid.UUID | None = None,
    thread_id: uuid.UUID | None = None,
) -> RoutedCommand:
    text = text.strip()
    if not text:
        raise ValueError("Comando vazio")

    recent = get_recent_thread(db, actor_type, actor_id) if thread_id is None else db.get(ConversationThread, thread_id)
    thread = recent
    reused_thread = False

    device = resolve_device(db, text, explicit_device_id)
    continuation = _is_continuation(text)

    if device is None and continuation:
        device = _active_device_from_context(db, recent)
        reused_thread = device is not None and recent is not None

    if device is None:
        device = resolve_device(db, text, None)

    if device is None:
        device = _active_device_from_context(db, recent)
        reused_thread = device is not None and recent is not None

    if device is None:
        raise ValueError("Não encontrei o dispositivo. Menciona o nome ou usa um comando mais explícito.")

    if thread is None:
        thread = get_or_create_thread(
            db,
            actor_type=actor_type,
            actor_id=actor_id,
            origin_channel="brain",
            subject=f"{text[:60]}",
            force_new=not reused_thread,
        )
    elif not reused_thread and thread.last_target_device_id and thread.last_target_device_id != device.id:
        thread = get_or_create_thread(
            db,
            actor_type=actor_type,
            actor_id=actor_id,
            origin_channel="brain",
            subject=f"{text[:60]}",
            force_new=True,
        )

    try:
        parsed = parse_natural_command(db, text, device.id)
    except ValueError:
        if continuation:
            reused = _reuse_last_command(db, thread if reused_thread else recent)
            if reused is None:
                raise
            intent, payload = reused
            parsed = type(
                "_Parsed",
                (),
                {
                    "type": intent,
                    "payload": payload,
                    "confidence": "medium",
                },
            )()
        else:
            raise
    confidence = parsed.confidence
    if continuation and reused_thread:
        confidence = "medium"

    record_thread_event(
        db,
        thread,
        kind="route_decision",
        payload={
            "text": text,
            "device_id": str(device.id),
            "device_name": device.name,
            "intent": parsed.type,
            "confidence": confidence,
            "reused_thread": reused_thread,
        },
        intent=parsed.type,
        target_device_id=device.id,
        summary=f"{parsed.type} -> {device.name}",
    )

    return RoutedCommand(
        thread=thread,
        device=device,
        intent=parsed.type,
        payload=parsed.payload,
        confidence=confidence,
        thread_reused=reused_thread,
    )
