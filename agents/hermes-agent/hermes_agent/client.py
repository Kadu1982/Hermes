from __future__ import annotations

from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class HermesClient:
    def __init__(self, base_url: str, device_token: str) -> None:
        self.base = base_url.rstrip("/") + "/api/v1"
        self.session = requests.Session()
        retry = Retry(
            total=3,
            connect=3,
            read=3,
            backoff_factor=0.5,
            status_forcelist=(502, 503, 504),
            allowed_methods=("GET", "POST"),
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=4, pool_maxsize=4)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.session.headers.update(
            {
                "Authorization": f"Bearer {device_token}",
                "Connection": "close",
            }
        )

    def heartbeat(self, inventory: dict[str, Any]) -> None:
        r = self.session.post(
            f"{self.base}/devices/me/heartbeat",
            json={
                "inventory": inventory,
                "app_version": "hermes-agent",
                "os_version": inventory.get("os_version"),
            },
            timeout=30,
        )
        self._finish_no_content(r)

    def next_command(self) -> dict[str, Any] | None:
        r = self.session.get(f"{self.base}/devices/me/commands/next", timeout=30)
        if r.status_code == 204:
            self._finish_no_content(r)
            return None
        try:
            r.raise_for_status()
            return r.json()
        finally:
            r.close()

    def complete(self, command_id: str, status: str, result: dict | None, logs: str | None = None) -> None:
        r = self.session.post(
            f"{self.base}/devices/me/commands/{command_id}/complete",
            json={"status": status, "result": result, "logs": logs},
            timeout=60,
        )
        self._finish_no_content(r)

    @staticmethod
    def _finish_no_content(r: requests.Response) -> None:
        """Evita RemoteDisconnected no Windows ao ler resposta 204 sem corpo."""
        try:
            r.raise_for_status()
        finally:
            r.close()

    @staticmethod
    def pair(base_url: str, pairing_code: str, device_name: str, platform: str) -> dict[str, Any]:
        url = base_url.rstrip("/") + "/api/v1/devices/pair"
        r = requests.post(
            url,
            json={
                "pairing_code": pairing_code.strip().upper().replace(" ", ""),
                "device_name": device_name,
                "platform": platform,
            },
            timeout=30,
            headers={"Connection": "close"},
        )
        r.raise_for_status()
        return r.json()
