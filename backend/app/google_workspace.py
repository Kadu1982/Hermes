from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import get_settings


class GoogleWorkspaceError(RuntimeError):
    pass


_DESTRUCTIVE_ACTIONS = {
    ("gmail", "modify"),
    ("calendar", "delete"),
    ("drive", "share"),
    ("drive", "delete"),
    ("sheets", "update"),
    ("sheets", "append"),
    ("docs", "append"),
}


@dataclass(frozen=True)
class GoogleWorkspaceResult:
    service: str
    action: str
    ok: bool
    summary: str | None
    data: Any
    raw_output: str


def _settings():
    return get_settings()


def _python_path() -> str:
    path = Path(_settings().google_workspace_python).expanduser()
    return str(path)


def _script_path() -> str:
    path = Path(_settings().google_workspace_api_script).expanduser()
    return str(path)


def _setup_path() -> str:
    path = Path(_settings().google_workspace_setup_script).expanduser()
    return str(path)


def auth_check() -> bool:
    proc = subprocess.run(
        [_python_path(), _setup_path(), "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0


def is_destructive(service: str, action: str) -> bool:
    return (service, action) in _DESTRUCTIVE_ACTIONS


def _as_cli_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def build_command(service: str, action: str, params: dict[str, Any], confirm: bool = False) -> list[str]:
    service = service.strip().lower()
    action = action.strip().lower()
    cmd = [_python_path(), _script_path(), service, action]

    def add_flag(flag: str, value: Any | None, *, allow_empty: bool = False) -> None:
        if value is None:
            return
        if isinstance(value, str) and not value and not allow_empty:
            return
        if isinstance(value, bool):
            if value:
                cmd.append(flag)
            return
        cmd.extend([flag, _as_cli_value(value)])

    if service == "gmail":
        if action == "search":
            cmd.append(_as_cli_value(params["query"]))
            add_flag("--max", params.get("max"))
        elif action == "get":
            cmd.append(_as_cli_value(params["message_id"]))
        elif action == "send":
            add_flag("--to", params["to"])
            add_flag("--subject", params["subject"])
            add_flag("--body", params["body"])
            add_flag("--cc", params.get("cc"), allow_empty=True)
            add_flag("--from", params.get("from_header"), allow_empty=True)
            add_flag("--html", params.get("html", False))
            add_flag("--thread-id", params.get("thread_id"), allow_empty=True)
        elif action == "reply":
            cmd.append(_as_cli_value(params["message_id"]))
            add_flag("--body", params["body"])
            add_flag("--from", params.get("from_header"), allow_empty=True)
        elif action == "labels":
            pass
        elif action == "modify":
            cmd.append(_as_cli_value(params["message_id"]))
            add_flag("--add-labels", params.get("add_labels"), allow_empty=True)
            add_flag("--remove-labels", params.get("remove_labels"), allow_empty=True)
            if confirm:
                cmd.append("--confirm")
        else:
            raise GoogleWorkspaceError(f"Unsupported Gmail action: {action}")
    elif service == "calendar":
        if action == "list":
            add_flag("--start", params.get("start"), allow_empty=True)
            add_flag("--end", params.get("end"), allow_empty=True)
            add_flag("--max", params.get("max"))
            add_flag("--calendar", params.get("calendar"), allow_empty=True)
        elif action == "create":
            add_flag("--summary", params["summary"])
            add_flag("--start", params["start"])
            add_flag("--end", params["end"])
            add_flag("--location", params.get("location"), allow_empty=True)
            add_flag("--description", params.get("description"), allow_empty=True)
            attendees = params.get("attendees")
            if attendees:
                add_flag("--attendees", attendees)
            add_flag("--calendar", params.get("calendar"), allow_empty=True)
        elif action == "delete":
            cmd.append(_as_cli_value(params["event_id"]))
            add_flag("--calendar", params.get("calendar"), allow_empty=True)
            if confirm:
                cmd.append("--confirm")
        else:
            raise GoogleWorkspaceError(f"Unsupported Calendar action: {action}")
    elif service == "drive":
        if action == "search":
            cmd.append(_as_cli_value(params["query"]))
            add_flag("--max", params.get("max"))
            add_flag("--raw-query", params.get("raw_query", False))
        elif action == "get":
            cmd.append(_as_cli_value(params["file_id"]))
        elif action == "upload":
            cmd.append(_as_cli_value(params["path"]))
            add_flag("--name", params.get("name"), allow_empty=True)
            add_flag("--parent", params.get("parent"), allow_empty=True)
            add_flag("--mime-type", params.get("mime_type"), allow_empty=True)
        elif action == "download":
            cmd.append(_as_cli_value(params["file_id"]))
            add_flag("--output", params.get("output"), allow_empty=True)
            add_flag("--export-mime", params.get("export_mime"), allow_empty=True)
        elif action == "create-folder":
            cmd.append(_as_cli_value(params["name"]))
            add_flag("--parent", params.get("parent"), allow_empty=True)
        elif action == "share":
            cmd.append(_as_cli_value(params["file_id"]))
            add_flag("--role", params.get("role"))
            add_flag("--type", params.get("type"))
            add_flag("--email", params.get("email"), allow_empty=True)
            add_flag("--domain", params.get("domain"), allow_empty=True)
            add_flag("--notify", params.get("notify", False))
            if confirm:
                cmd.append("--confirm")
        elif action == "delete":
            cmd.append(_as_cli_value(params["file_id"]))
            add_flag("--permanent", params.get("permanent", False))
            if confirm:
                cmd.append("--confirm")
        else:
            raise GoogleWorkspaceError(f"Unsupported Drive action: {action}")
    elif service == "contacts":
        if action == "list":
            add_flag("--max", params.get("max"))
        else:
            raise GoogleWorkspaceError(f"Unsupported Contacts action: {action}")
    elif service == "sheets":
        if action == "get":
            cmd.append(_as_cli_value(params["sheet_id"]))
            cmd.append(_as_cli_value(params["range"]))
        elif action == "update":
            cmd.append(_as_cli_value(params["sheet_id"]))
            cmd.append(_as_cli_value(params["range"]))
            add_flag("--values", params["values"])
            if confirm:
                cmd.append("--confirm")
        elif action == "append":
            cmd.append(_as_cli_value(params["sheet_id"]))
            cmd.append(_as_cli_value(params["range"]))
            add_flag("--values", params["values"])
            if confirm:
                cmd.append("--confirm")
        elif action == "create":
            add_flag("--title", params["title"])
            add_flag("--sheet-name", params.get("sheet_name"), allow_empty=True)
        else:
            raise GoogleWorkspaceError(f"Unsupported Sheets action: {action}")
    elif service == "docs":
        if action == "get":
            cmd.append(_as_cli_value(params["doc_id"]))
        elif action == "create":
            add_flag("--title", params["title"])
            add_flag("--body", params.get("body"), allow_empty=True)
        elif action == "append":
            cmd.append(_as_cli_value(params["doc_id"]))
            add_flag("--text", params["text"])
            if confirm:
                cmd.append("--confirm")
        else:
            raise GoogleWorkspaceError(f"Unsupported Docs action: {action}")
    else:
        raise GoogleWorkspaceError(f"Unsupported service: {service}")

    return cmd


def run(service: str, action: str, params: dict[str, Any], *, confirm: bool = False) -> GoogleWorkspaceResult:
    if is_destructive(service, action) and not confirm:
        raise GoogleWorkspaceError(
            f"Action {service}.{action} requires confirm=true"
        )
    cmd = build_command(service, action, params, confirm=confirm)
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    raw = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    if proc.returncode != 0:
        raise GoogleWorkspaceError(err or raw or f"Google Workspace command failed with exit code {proc.returncode}")
    data: Any
    if not raw:
        data = None
    else:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = raw
    summary = data.get("summary") if isinstance(data, dict) else None
    return GoogleWorkspaceResult(
        service=service,
        action=action,
        ok=True,
        summary=summary,
        data=data,
        raw_output=raw,
    )

