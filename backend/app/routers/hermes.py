from __future__ import annotations

from fastapi import APIRouter, Depends

from app.deps import get_current_admin
from app.models import User
from app.notify_service import load_voice_profile

router = APIRouter(prefix="/hermes", tags=["hermes"])


@router.get("/voice-profile")
def voice_profile(_: User = Depends(get_current_admin)) -> dict:
    """Single Hermes voice identity — same profile for app, VPS TTS, and desktop agents."""
    return load_voice_profile()
