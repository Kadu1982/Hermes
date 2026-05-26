"""Aguardar conclusão de comandos na fila (cérebro / CLI)."""

from __future__ import annotations

import time
import uuid

from sqlalchemy.orm import Session

from app.models import Command


def wait_for_command(
    db: Session,
    command_id: uuid.UUID,
    *,
    timeout_seconds: int = 90,
    poll_interval: float = 1.0,
) -> Command:
    deadline = time.monotonic() + max(timeout_seconds, 1)
    while time.monotonic() < deadline:
        db.expire_all()
        cmd = db.get(Command, command_id)
        if cmd is None:
            raise ValueError("command not found")
        if cmd.status in ("done", "failed"):
            return cmd
        time.sleep(poll_interval)
    cmd = db.get(Command, command_id)
    if cmd is None:
        raise ValueError("command not found")
    return cmd


def format_command_result_message(
    *,
    device_name: str,
    command_type: str,
    status: str,
    result: dict | None,
    logs: str | None = None,
) -> str:
    if status == "pending":
        return (
            f"Comando {command_type} enviado para {device_name}, mas ainda está pendente "
            f"(o agente não concluiu em tempo). Verifique se o agente/app está ativo."
        )
    if status == "failed":
        detail = result or {}
        err = detail.get("error") or logs or str(detail) or "erro desconhecido"
        return f"Comando {command_type} em {device_name}: FALHOU — {err}"

    if command_type == "ping":
        pong = (result or {}).get("pong")
        if pong is True:
            return f"Ping em {device_name}: OK (pong=true)."
        if pong is False:
            return f"Ping em {device_name}: respondeu com pong=false."
        return f"Ping em {device_name}: concluído — {result or {}}"

    if command_type == "server_docker_ps":
        containers = (result or {}).get("containers") or (result or {}).get("items") or result
        if isinstance(containers, list):
            if not containers:
                return f"Docker em {device_name}: nenhum container em execução."
            lines = [f"Docker em {device_name} ({len(containers)} container(s)):"]
            for c in containers[:20]:
                if isinstance(c, dict):
                    name = c.get("name") or c.get("Names") or c.get("ID", "?")
                    state = c.get("status") or c.get("State") or c.get("Status", "")
                    lines.append(f"  • {name} — {state}".rstrip(" —"))
                elif isinstance(c, str) and "\t" in c:
                    name, _, state = c.partition("\t")
                    lines.append(f"  • {name} — {state}".rstrip(" —"))
                else:
                    lines.append(f"  • {c}")
            if len(containers) > 20:
                lines.append(f"  … e mais {len(containers) - 20}")
            return "\n".join(lines)
        return f"Docker em {device_name}: {result}"

    if command_type == "get_inventory":
        return f"Inventário de {device_name} obtido."

    if command_type == "speak":
        return f"Falado em {device_name}: {(result or {}).get('spoken', 'ok')}"

    if command_type == "take_photo":
        detail = result or {}
        if detail.get("archived_path"):
            base = f"Foto capturada em {device_name} e arquivada localmente."
            if detail.get("share_requested"):
                base += " Houve pedido de compartilhamento, mas o arquivo ficou guardado primeiro."
            return base + f" Caminho: {detail.get('archived_path')}"
        return f"Foto capturada em {device_name}: {detail or 'concluída'}"

    if command_type == "get_location":
        detail = result or {}
        if detail.get("latitude") is not None and detail.get("longitude") is not None:
            coords = f"{detail.get('latitude')}, {detail.get('longitude')}"
            maps = detail.get("maps_url")
            if maps:
                return f"Localização de {device_name}: {coords} ({maps})"
            return f"Localização de {device_name}: {coords}"
        return f"Localização de {device_name}: {detail or 'concluída'}"

    if command_type == "navigate_to":
        detail = result or {}
        destination = detail.get("destination") or (detail.get("maps_url") and "rota aberta")
        if detail.get("opened_url"):
            return f"Navegação aberta em {device_name} para {destination}: {detail.get('opened_url')}"
        return f"Navegação aberta em {device_name} para {destination}"

    if command_type == "open_app":
        detail = result or {}
        app_name = detail.get("app_name") or (result or {}).get("label") or "app"
        if detail.get("opened"):
            return f"App aberto em {device_name}: {app_name}"
        return f"App em {device_name}: {app_name} — concluído"

    if command_type == "android_system_action":
        detail = result or {}
        action = detail.get("action") or "ação de sistema"
        if detail.get("performed"):
            return f"Ação de sistema em {device_name}: {action}"
        return f"Ação de sistema em {device_name}: {action} — concluída"

    if command_type == "android_deep_link":
        detail = result or {}
        target = detail.get("target") or "destino"
        if detail.get("opened"):
            return f"Atalho Android aberto em {device_name}: {target}"
        return f"Atalho Android em {device_name}: {target} — concluído"

    if command_type == "request_unlock":
        detail = result or {}
        if detail.get("dismissed"):
            return f"Desbloqueio solicitado em {device_name}: confirmado pelo sistema."
        if detail.get("approved"):
            return f"Desbloqueio solicitado em {device_name}: aprovado, aguardando sistema."
        return f"Desbloqueio solicitado em {device_name}: concluído"

    if command_type == "android_ui_action":
        detail = result or {}
        flow = detail.get("flow") or "ui_action"
        if detail.get("performed"):
            return f"Ação UI em {device_name}: {flow}"
        return f"Ação UI em {device_name}: {flow} — concluída"

    return f"Comando {command_type} em {device_name}: concluído — {result or 'sem payload'}"
