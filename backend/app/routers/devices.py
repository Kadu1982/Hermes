from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit_service import safe_metadata, write_audit
from app.db import get_db
from app.deps import get_current_admin, get_current_device
from app.models import Command, Device, PairingCode, User
from app.rate_limit import limiter
from app.schemas import (
    DeviceDetail,
    DeviceMe,
    DevicePairRequest,
    DevicePairResponse,
    DeviceSummary,
    HeartbeatRequest,
)
from app.security import hash_device_secret, new_device_token, verify_pairing_code

router = APIRouter(prefix="/devices", tags=["devices"])


@router.post("/pair", response_model=DevicePairResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
def pair_device(body: DevicePairRequest, request: Request, db: Session = Depends(get_db)) -> DevicePairResponse:
    now = datetime.now(tz=UTC)
    candidates = (
        db.query(PairingCode)
        .filter(PairingCode.consumed_at.is_(None), PairingCode.expires_at > now)
        .all()
    )
    match: PairingCode | None = None
    for pc in candidates:
        if verify_pairing_code(body.pairing_code, pc.code_hash):
            match = pc
            break
    if match is None:
        write_audit(
            db,
            actor_type="device",
            actor_id=None,
            action="pairing_failed",
            metadata=safe_metadata({"reason": "invalid_or_expired"}),
        )
        db.commit()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired pairing code")
    match.consumed_at = now
    platform = (body.platform or "android").strip().lower()
    if platform not in ("android", "windows", "linux", "macos", "server"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid platform")
    device = Device(
        name=body.device_name.strip(),
        platform=platform,
        token_hash="",
        pairing_code_id=match.id,
        public_key=body.public_key,
    )
    db.add(device)
    db.flush()
    token, secret = new_device_token(device.id)
    device.token_hash = hash_device_secret(secret)
    write_audit(
        db,
        actor_type="device",
        actor_id=str(device.id),
        action="device_paired",
        metadata=safe_metadata({"pairing_code_id": str(match.id)}),
    )
    db.commit()
    return DevicePairResponse(device_id=device.id, device_token=token)


@router.get("/me", response_model=DeviceMe)
def device_me(device: Device = Depends(get_current_device)) -> DeviceMe:
    return DeviceMe(
        id=device.id,
        name=device.name,
        platform=device.platform,
        last_seen=device.last_seen,
        revoked_at=device.revoked_at,
        policy_version=device.token_version,
        inventory=device.last_inventory,
    )


@router.post("/me/heartbeat", status_code=status.HTTP_204_NO_CONTENT)
def device_heartbeat(
    body: HeartbeatRequest,
    db: Session = Depends(get_db),
    device: Device = Depends(get_current_device),
) -> Response:
    now = datetime.now(tz=UTC)
    device.last_seen = now
    inv = {}
    if body.inventory:
        inv.update(body.inventory)
    if body.battery_percent is not None:
        inv["battery_percent"] = body.battery_percent
    if body.network_type:
        inv["network_type"] = body.network_type
    if body.app_version:
        inv["app_version"] = body.app_version
    if body.os_version:
        inv["os_version"] = body.os_version
    device.last_inventory = inv or device.last_inventory
    db.add(device)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/me/rotate-token")
def rotate_device_token(db: Session = Depends(get_db), device: Device = Depends(get_current_device)):
    token, secret = new_device_token(device.id)
    device.token_hash = hash_device_secret(secret)
    device.token_version += 1
    write_audit(
        db,
        actor_type="device",
        actor_id=str(device.id),
        action="device_token_rotated",
        metadata=None,
    )
    db.commit()
    return {"device_token": token}


@router.get("", response_model=dict)
def list_devices(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
    limit: int = 50,
    offset: int = 0,
) -> dict:
    limit = min(max(limit, 1), 100)
    offset = max(offset, 0)
    q = select(Device).order_by(Device.created_at.desc()).offset(offset).limit(limit)
    items = db.scalars(q).all()
    total = db.scalar(select(func.count()).select_from(Device)) or 0
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
        "total": total,
    }


@router.get("/{device_id}", response_model=DeviceDetail)
def get_device(
    device_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> DeviceDetail:
    device = db.get(Device, device_id)
    if device is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Device not found")
    _ = admin
    return DeviceDetail(
        id=device.id,
        name=device.name,
        platform=device.platform,
        last_seen=device.last_seen,
        revoked_at=device.revoked_at,
        policy_version=device.token_version,
        token_version=device.token_version,
        inventory=device.last_inventory,
        public_key=device.public_key,
        created_at=device.created_at,
    )


@router.post("/{device_id}/revoke", status_code=status.HTTP_204_NO_CONTENT)
def revoke_device(
    device_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> Response:
    device = db.get(Device, device_id)
    if device is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Device not found")
    device.revoked_at = datetime.now(tz=UTC)
    device.token_version += 1
    write_audit(
        db,
        actor_type="user",
        actor_id=str(admin.id),
        action="device_revoked",
        metadata=safe_metadata({"device_id": str(device.id)}),
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
