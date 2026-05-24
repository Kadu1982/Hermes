#!/usr/bin/env python3
"""
CLI para o cérebro Hermes (~/.hermes) controlar dispositivos jarvis-horizon.

Uso:
  export HERMES_BRAIN_SERVICE_KEY=...
  export JARVIS_API_URL=http://127.0.0.1:18080
  python3 scripts/jarvis_brain_cli.py devices
  python3 scripts/jarvis_brain_cli.py command "ping no PC-Casa"
  python3 scripts/jarvis_brain_cli.py command "lista docker na VPS" --wait 90
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def api_base() -> str:
    return os.environ.get("JARVIS_API_URL", "http://127.0.0.1:18080").rstrip("/")


def brain_key() -> str:
    key = os.environ.get("HERMES_BRAIN_SERVICE_KEY", "").strip()
    if not key:
        print("ERRO: defina HERMES_BRAIN_SERVICE_KEY", file=sys.stderr)
        sys.exit(1)
    return key


def request(method: str, path: str, body: dict | None = None) -> dict:
    url = f"{api_base()}/api/v1{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Content-Type": "application/json",
            "X-Hermes-Brain-Key": brain_key(),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"HTTP {e.code}: {err}", file=sys.stderr)
        sys.exit(1)


def cmd_devices(_: argparse.Namespace) -> None:
    out = request("GET", "/brain/devices")
    for d in out.get("items", []):
        print(f"- {d['name']} ({d['platform']}) id={d['id']}")


def cmd_command(args: argparse.Namespace) -> None:
    body = {
        "text": args.text,
        "notify_channel": "silent",
        "wait_timeout_seconds": args.wait,
    }
    out = request("POST", "/brain/command", body)
    # Mensagem já inclui resultado (ping pong=true, docker list, etc.)
    print(out.get("message", out))
    if args.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))


def cmd_status(_: argparse.Namespace) -> None:
    out = request("GET", "/brain/status")
    print(json.dumps(out, indent=2))


def main() -> None:
    p = argparse.ArgumentParser(description="Jarvis brain → dispositivos (API jarvis-horizon)")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status", help="Verificar ponte cérebro↔API").set_defaults(func=cmd_status)
    sub.add_parser("devices", help="Listar dispositivos pareados").set_defaults(func=cmd_devices)
    c = sub.add_parser("command", help="Enviar comando em linguagem natural e aguardar resultado")
    c.add_argument("text", help='Ex.: "ping no PC-Casa"')
    c.add_argument(
        "--wait",
        type=int,
        default=90,
        metavar="SEC",
        help="Segundos para aguardar conclusão (0=só enfileirar)",
    )
    c.add_argument("--json", action="store_true", help="Imprimir JSON completo após a mensagem")
    c.set_defaults(func=cmd_command)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
