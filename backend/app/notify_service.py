from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models import Command, Device, User

logger = logging.getLogger("hermes.notify")

VOICE_PROFILE_PATH = Path(__file__).resolve().parent / "hermes_voice.json"


def load_voice_profile() -> dict[str, Any]:
    if VOICE_PROFILE_PATH.is_file():
        return json.loads(VOICE_PROFILE_PATH.read_text(encoding="utf-8"))
    return {
        "display_name": "Jarvis",
        "locale": "pt-BR",
        "edge_tts_voice": "pt-BR-AntonioNeural",
        "pitch": 0.82,
        "speech_rate": 0.86,
        "ready_spoken": "Jarvis à sua disposição, senhor.",
        "task_done_spoken": "Concluído, senhor.",
        "task_failed_spoken": "Peço desculpas, senhor.",
    }


def notify_command_finished(db: Session, cmd: Command, device: Device) -> None:
    if not cmd.notify_channel:
        return
    channel = cmd.notify_channel
    on = cmd.notify_on or "done"
    if on == "done" and cmd.status != "done":
        return
    if on == "failed" and cmd.status != "failed":
        return
    if on == "both" and cmd.status not in ("done", "failed"):
        return

    profile = load_voice_profile()
    title = profile.get("display_name", "Hermes")
    body = f"{device.name}: {cmd.type} → {cmd.status}"
    if cmd.source_text:
        body = f"{cmd.source_text[:120]} — {cmd.status}"
    if cmd.result:
        body = f"{body} | result={cmd.result}"

    # MVP: log + store in result metadata for app poll; push/email in later phases
    logger.info("notify channel=%s title=%s body=%s", channel, title, body)

    if channel == "push":
        # FCM phase 2 — placeholder
        pass
    elif channel == "voice":
        # Agents/app read voice profile and speak task_done_spoken / task_failed_spoken
        pass
