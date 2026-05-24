from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.audit_service import safe_metadata, write_audit
from app.config import get_settings
from app.db import get_db
from app.deps import get_current_device
from app.models import Command, Device, FileRecord

router = APIRouter(prefix="/files", tags=["files"])
settings = get_settings()


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_file(
    command_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    device: Device = Depends(get_current_device),
):
    cmd = db.get(Command, command_id)
    if cmd is None or cmd.device_id != device.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Command not found")
    if db.query(FileRecord).filter(FileRecord.command_id == command_id).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "File already uploaded for this command")
    max_bytes = settings.max_upload_mb * 1024 * 1024
    settings.files_dir.mkdir(parents=True, exist_ok=True)
    safe_filename = Path(file.filename or "upload.bin").name or "upload.bin"
    dest_name = f"{command_id}_{safe_filename}"
    dest_path = settings.files_dir / dest_name
    h = hashlib.sha256()
    size = 0
    with dest_path.open("wb") as out:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > max_bytes:
                out.close()
                dest_path.unlink(missing_ok=True)
                raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File too large")
            h.update(chunk)
            out.write(chunk)
    digest = h.hexdigest()
    rel_path = str(dest_path.relative_to(settings.files_dir.resolve()))
    rec = FileRecord(
        device_id=device.id,
        command_id=command_id,
        filename=file.filename or "upload.bin",
        storage_path=rel_path,
        size_bytes=size,
        sha256=digest,
    )
    db.add(rec)
    write_audit(
        db,
        actor_type="device",
        actor_id=str(device.id),
        action="file_uploaded",
        metadata=safe_metadata({"file_id": str(rec.id), "command_id": str(command_id), "size": size}),
    )
    db.commit()
    db.refresh(rec)
    return {
        "id": rec.id,
        "filename": rec.filename,
        "size_bytes": rec.size_bytes,
        "sha256": rec.sha256,
        "command_id": rec.command_id,
    }


@router.get("/{file_id}/download")
def download_file(
    file_id: uuid.UUID,
    db: Session = Depends(get_db),
    device: Device = Depends(get_current_device),
):
    rec = db.get(FileRecord, file_id)
    if rec is None or rec.device_id != device.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found")
    base_dir = settings.files_dir.resolve()
    path = (base_dir / rec.storage_path).resolve()
    try:
        path.relative_to(base_dir)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File missing on server") from exc
    if not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File missing on server")
    write_audit(
        db,
        actor_type="device",
        actor_id=str(device.id),
        action="file_downloaded",
        metadata=safe_metadata({"file_id": str(rec.id)}),
    )
    db.commit()
    return FileResponse(path, filename=rec.filename, media_type="application/octet-stream")
