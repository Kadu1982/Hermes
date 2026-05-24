from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


def _normalize_email(value: str) -> str:
    """Accept internal domains (.local) rejected by EmailStr."""
    v = value.lower().strip()
    if "@" not in v or v.startswith("@") or v.endswith("@"):
        raise ValueError("invalid email address")
    local, _, domain = v.partition("@")
    if not local or not domain or "." not in domain:
        raise ValueError("invalid email address")
    return v


class AdminLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _normalize_email(value)


class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    requires_2fa: bool


class TwoFactorVerifyRequest(BaseModel):
    access_token: str
    code: str = Field(min_length=6, max_length=8)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CreatePairingCodeRequest(BaseModel):
    label: str | None = Field(default=None, max_length=120)


class CreatePairingCodeResponse(BaseModel):
    id: uuid.UUID
    code: str
    expires_at: datetime


class DevicePairRequest(BaseModel):
    pairing_code: str
    device_name: str = Field(max_length=120)
    platform: str = Field(default="android", max_length=32)
    public_key: str | None = None


class DevicePairResponse(BaseModel):
    device_id: uuid.UUID
    device_token: str


class DeviceSummary(BaseModel):
    id: uuid.UUID
    name: str
    platform: str
    last_seen: datetime | None
    revoked_at: datetime | None

    class Config:
        from_attributes = True


class DeviceMe(DeviceSummary):
    policy_version: int = 1
    inventory: dict[str, Any] | None = None


class DeviceDetail(DeviceSummary):
    policy_version: int = 1
    token_version: int
    inventory: dict[str, Any] | None = None
    public_key: str | None = None
    created_at: datetime


class HeartbeatRequest(BaseModel):
    battery_percent: float | None = None
    network_type: str | None = None
    app_version: str | None = None
    os_version: str | None = None
    inventory: dict[str, Any] | None = None


class CreateCommandRequest(BaseModel):
    type: str
    payload: dict[str, Any] | None = None
    notify_channel: str | None = Field(default=None, pattern="^(push|voice|silent)$")
    notify_on: str | None = Field(default="done", pattern="^(done|failed|both)$")
    source_text: str | None = Field(default=None, max_length=2000)
    thread_id: uuid.UUID | None = None


class NaturalCommandRequest(BaseModel):
    text: str = Field(min_length=2, max_length=2000)
    device_id: uuid.UUID | None = None
    thread_id: uuid.UUID | None = None
    notify_channel: str | None = Field(default="voice", pattern="^(push|voice|silent)$")
    notify_on: str | None = Field(default="done", pattern="^(done|failed|both)$")


class CommandJob(BaseModel):
    id: uuid.UUID
    type: str
    payload: dict[str, Any] | None
    status: str
    thread_id: uuid.UUID | None = None

    class Config:
        from_attributes = True


class CommandJobAdmin(CommandJob):
    result: dict[str, Any] | None
    created_at: datetime
    completed_at: datetime | None
    created_by_user_id: uuid.UUID | None = None
    created_by_device_id: uuid.UUID | None = None
    notify_channel: str | None = None
    notify_on: str | None = None
    source_text: str | None = None

    class Config:
        from_attributes = True


class NaturalCommandResponse(BaseModel):
    command: CommandJobAdmin
    parsed_device_name: str
    parsed_type: str
    confidence: str
    thread_id: uuid.UUID | None = None


class BrainCommandRequest(BaseModel):
    """Pedido do cérebro Hermes (gateway) para executar em dispositivos."""

    text: str = Field(min_length=2, max_length=4000)
    device_id: uuid.UUID | None = None
    thread_id: uuid.UUID | None = None
    notify_channel: str | None = Field(default="silent", pattern="^(push|voice|silent)$")
    notify_on: str | None = Field(default="done", pattern="^(done|failed|both)$")
    wait_timeout_seconds: int = Field(
        default=90,
        ge=0,
        le=300,
        description="Segundos para aguardar done/failed (0 = só enfileirar).",
    )


class BrainCommandResponse(BaseModel):
    command_id: uuid.UUID
    device_name: str
    command_type: str
    status: str
    message: str
    result: dict[str, Any] | None = None
    thread_id: uuid.UUID | None = None


class BrainGoogleRequest(BaseModel):
    text: str = Field(min_length=2, max_length=4000)
    confirm: bool = False
    thread_id: uuid.UUID | None = None


class BrainGoogleResponse(BaseModel):
    thread_id: uuid.UUID | None = None
    service: str
    action: str
    status: str
    message: str
    requires_confirmation: bool = False
    summary: str | None = None
    data: dict[str, Any] | list[dict[str, Any]] | list[Any] | dict[str, Any] | None = None
    raw_output: str | None = None


class BrainContextResponse(BaseModel):
    thread: ConversationThreadEntry | None = None
    recent_threads: list[ConversationThreadEntry] = Field(default_factory=list)


class BrainRawCommandRequest(BaseModel):
    device_name: str = Field(min_length=1, max_length=128)
    command_type: str = Field(min_length=1, max_length=64)
    payload: dict[str, Any] | None = None


class CommandCompleteRequest(BaseModel):
    status: str = Field(pattern="^(done|failed)$")
    result: dict[str, Any] | None = None
    logs: str | None = Field(default=None, max_length=65536)


class FileMetaResponse(BaseModel):
    id: uuid.UUID
    filename: str
    size_bytes: int
    sha256: str
    command_id: uuid.UUID


class AuditLogEntry(BaseModel):
    id: uuid.UUID
    actor_type: str
    actor_id: str | None
    action: str
    metadata: dict[str, Any] | None
    created_at: datetime

    class Config:
        from_attributes = True


class MemoryEventEntry(BaseModel):
    id: uuid.UUID
    thread_id: uuid.UUID
    command_id: uuid.UUID | None
    kind: str
    payload: dict[str, Any] | None
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationThreadEntry(BaseModel):
    id: uuid.UUID
    actor_type: str
    actor_id: str | None
    origin_channel: str | None
    subject: str | None
    summary: str | None
    last_intent: str | None
    last_target_device_id: uuid.UUID | None
    last_command_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    events: list[MemoryEventEntry] = Field(default_factory=list)

    class Config:
        from_attributes = True
