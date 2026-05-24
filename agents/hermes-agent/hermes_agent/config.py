from __future__ import annotations

import json
import platform
from pathlib import Path

from platformdirs import user_config_dir

CONFIG_DIR = Path(user_config_dir("hermes-agent"))
CONFIG_FILE = CONFIG_DIR / "config.json"


def default_platform() -> str:
    sys = platform.system().lower()
    if sys == "darwin":
        return "macos"
    if sys == "windows":
        return "windows"
    if sys == "linux":
        # Heuristic: VPS brain often runs agent alongside API
        return "linux"
    return "linux"


def load_config() -> dict:
    if CONFIG_FILE.is_file():
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    return {}


def save_config(data: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
