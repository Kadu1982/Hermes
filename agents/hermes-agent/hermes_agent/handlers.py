from __future__ import annotations

import json
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Any

from hermes_agent.client import HermesClient
from hermes_agent.voice import speak_local


def collect_inventory() -> dict[str, Any]:
    total, used, free = shutil.disk_usage("/")
    return {
        "hostname": platform.node(),
        "os_version": f"{platform.system()} {platform.release()}",
        "platform": platform.system().lower(),
        "storage_total_bytes": total,
        "storage_free_bytes": free,
        "storage_used_bytes": used,
    }


def handle_command(cmd: dict[str, Any]) -> tuple[str, dict[str, Any] | None, str | None]:
    ctype = cmd.get("type")
    try:
        if ctype == "ping":
            return "done", {"pong": True}, None
        if ctype == "get_inventory":
            return "done", {"inventory": collect_inventory()}, None
        if ctype == "server_disk":
            inv = collect_inventory()
            return "done", {"disk": inv}, None
        if ctype == "server_docker_ps":
            proc = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}\t{{.Status}}"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if proc.returncode != 0:
                return "failed", {"error": proc.stderr or "docker failed"}, proc.stderr
            lines = [ln for ln in proc.stdout.strip().split("\n") if ln]
            return "done", {"containers": lines}, None
        if ctype == "noop":
            return "done", {}, None
        if ctype == "speak":
            text = str((cmd.get("payload") or {}).get("text") or "Olá, senhor.")
            speak_local(text)
            return "done", {"spoken": text}, None
        return "failed", {"error": f"unsupported:{ctype}"}, None
    except Exception as exc:
        return "failed", {"error": str(exc)}, str(exc)


def run_poll_loop(client: HermesClient) -> None:
    inv = collect_inventory()
    client.heartbeat(inv)
    cmd = client.next_command()
    if not cmd:
        return
    status, result, logs = handle_command(cmd)
    client.complete(cmd["id"], status, result, logs)
