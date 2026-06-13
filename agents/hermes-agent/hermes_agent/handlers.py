from __future__ import annotations

import json
import mimetypes
import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from hermes_agent.client import HermesClient
from hermes_agent.voice import speak_local

_MAX_INLINE_TEXT_SIZE = 100_000  # 100 KB


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


def handle_command(cmd: dict[str, Any], client: HermesClient | None = None) -> tuple[str, dict[str, Any] | None, str | None]:
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
        if ctype == "take_screenshot":
            return _handle_screenshot(client, cmd)
        if ctype == "read_local_file":
            return _handle_read_local_file(client, cmd)
        if ctype == "restart_agent":
            return _handle_restart_agent(client, cmd)
        if ctype == "restart_pc":
            return _handle_restart_pc(client, cmd)
        return "failed", {"error": f"unsupported:{ctype}"}, None
    except Exception as exc:
        return "failed", {"error": str(exc)}, str(exc)


def _capture_screenshot() -> str:
    """Capture a screenshot and return the path to a temporary PNG file.

    Backend selection (first match wins):
      1. Browser page — if JARVIS_SCREENSHOT_BROWSER_URL is set *and* playwright
         is importable, screenshot the page via Chromium.
      2. Windows native — via PowerShell/.NET CopyFromScreen with no external
         Python dependency.
      3. Error — RuntimeError explaining what is missing.
    """
    browser_url = os.environ.get("JARVIS_SCREENSHOT_BROWSER_URL")

    if browser_url:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise RuntimeError(
                "JARVIS_SCREENSHOT_BROWSER_URL is set but playwright is not "
                "available. Install it with: pip install playwright && "
                "playwright install chromium"
            )
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp_path = tmp.name
        tmp.close()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                page.goto(browser_url, wait_until="networkidle")
                page.screenshot(path=tmp_path, full_page=True)
                browser.close()
            return tmp_path
        except Exception:
            Path(tmp_path).unlink(missing_ok=True)
            raise

    if platform.system() == "Windows":
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp_path = tmp.name
        tmp.close()
        try:
            ps_script = (
                "Add-Type -AssemblyName System.Drawing; "
                "Add-Type -AssemblyName System.Windows.Forms; "
                "$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds; "
                "$bmp = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height; "
                "$gfx = [System.Drawing.Graphics]::FromImage($bmp); "
                "$gfx.CopyFromScreen($bounds.X, $bounds.Y, 0, 0, $bounds.Size); "
                f"$bmp.Save('{tmp_path}', [System.Drawing.Imaging.ImageFormat]::Png); "
                "$gfx.Dispose(); "
                "$bmp.Dispose()"
            )
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                Path(tmp_path).unlink(missing_ok=True)
                raise RuntimeError(
                    f"PowerShell screenshot failed: "
                    f"{result.stderr or result.stdout}"
                )
            return tmp_path
        except Exception:
            Path(tmp_path).unlink(missing_ok=True)
            raise

    raise RuntimeError(
        "No screenshot backend available. "
        "On Windows, PowerShell is used natively. "
        "Alternatively, set JARVIS_SCREENSHOT_BROWSER_URL and install "
        "playwright."
    )


def _handle_screenshot(client: HermesClient, cmd: dict[str, Any]) -> tuple[str, dict[str, Any] | None, str | None]:
    try:
        tmp_path = _capture_screenshot()
    except Exception as exc:
        return "failed", {"error": str(exc)}, str(exc)
    try:
        upload_resp = client.upload_file(cmd["id"], tmp_path)
        return "done", {
            "file_id": upload_resp["id"],
            "filename": upload_resp["filename"],
            "size_bytes": upload_resp["size_bytes"],
            "sha256": upload_resp["sha256"],
        }, None
    except Exception as exc:
        return "failed", {"error": str(exc)}, str(exc)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _looks_like_text(raw: bytes) -> bool:
    if not raw:
        return True
    if b"\x00" in raw:
        return False
    try:
        decoded = raw.decode("utf-8")
    except UnicodeDecodeError:
        return False
    if not decoded:
        return True
    printable = sum(1 for ch in decoded if ch.isprintable() or ch in "\r\n\t")
    return (printable / len(decoded)) >= 0.85


def _handle_read_local_file(client: HermesClient | None, cmd: dict[str, Any]) -> tuple[str, dict[str, Any] | None, str | None]:
    filepath = str((cmd.get("payload") or {}).get("filepath", "")).strip()
    if not filepath:
        return "failed", {"error": "read_local_file requires filepath in payload"}, None

    path = Path(filepath)
    if not path.exists():
        return "failed", {"error": f"File not found: {filepath}"}, None
    if not path.is_file():
        return "failed", {"error": f"Path is not a file: {filepath}"}, None

    size = path.stat().st_size
    fname = path.name
    raw = path.read_bytes()

    if size <= _MAX_INLINE_TEXT_SIZE and _looks_like_text(raw):
        text_content = raw.decode("utf-8", errors="replace")
        return "done", {
            "filename": fname,
            "content": text_content,
            "content_type": "text",
            "size_bytes": size,
        }, None

    # Binary or large file — upload via API
    if client is None:
        return "failed", {"error": "Client required for file upload, no client available"}, None

    try:
        mime_type, _ = mimetypes.guess_type(fname)
        upload_resp = client.upload_file(cmd["id"], filepath, mime_type or "application/octet-stream")
        return "done", {
            "file_id": upload_resp["id"],
            "filename": upload_resp["filename"],
            "size_bytes": upload_resp["size_bytes"],
            "sha256": upload_resp["sha256"],
        }, None
    except Exception as exc:
        return "failed", {"error": str(exc)}, str(exc)


def _schedule_restart() -> None:
    import sys

    delay = 3
    if platform.system() == "Windows":
        ps_script = (
            "$ErrorActionPreference='SilentlyContinue'; "
            f"Start-Sleep -Seconds {delay}; "
            "Stop-ScheduledTask -TaskName 'HermesAgent' | Out-Null; "
            "Start-ScheduledTask -TaskName 'HermesAgent' | Out-Null"
        )
        creationflags = 0
        creationflags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)
        creationflags |= getattr(subprocess, "DETACHED_PROCESS", 0)
        creationflags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        subprocess.Popen(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_script],
            creationflags=creationflags,
            close_fds=True,
        )
    else:
        script = (
            f"sleep {delay} && "
            f"systemctl --user restart hermes-agent 2>/dev/null || "
            f"\"{sys.executable}\" -m hermes_agent run"
        )
        subprocess.Popen(
            ["sh", "-c", script],
            close_fds=True,
        )


def _handle_restart_agent(
    client: HermesClient | None, cmd: dict[str, Any]
) -> tuple[str, dict[str, Any] | None, str | None]:
    _schedule_restart()
    return "done", {"restarting": True, "message": "Agent restarting in 3 seconds..."}, None


def _schedule_reboot() -> None:
    import sys

    delay = 10
    if platform.system() == "Windows":
        ps_script = (
            f"Start-Sleep -Seconds {delay}; "
            "Restart-Computer -Force"
        )
        creationflags = 0
        creationflags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)
        creationflags |= getattr(subprocess, "DETACHED_PROCESS", 0)
        creationflags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        subprocess.Popen(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_script],
            creationflags=creationflags,
            close_fds=True,
        )
    else:
        script = (
            f"sleep {delay} && "
            "sudo reboot"
        )
        subprocess.Popen(
            ["sh", "-c", script],
            close_fds=True,
        )


def _handle_restart_pc(
    client: HermesClient | None, cmd: dict[str, Any]
) -> tuple[str, dict[str, Any] | None, str | None]:
    _schedule_reboot()
    return "done", {"rebooting": True, "message": "PC reiniciando em 10 segundos..."}, None


def run_poll_loop(client: HermesClient) -> bool:
    """Run one poll iteration. Returns True if agent restart was requested."""
    inv = collect_inventory()
    client.heartbeat(inv)
    cmd = client.next_command()
    if not cmd:
        return False
    status, result, logs = handle_command(cmd, client)
    client.complete(cmd["id"], status, result, logs)
    return cmd.get("type") in ("restart_agent", "restart_pc")
