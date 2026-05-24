from __future__ import annotations

import argparse
import time

from hermes_agent.client import HermesClient
from hermes_agent.config import default_platform, load_config, save_config
from hermes_agent.handlers import run_poll_loop


def cmd_pair(args: argparse.Namespace) -> None:
    data = HermesClient.pair(args.server, args.code, args.name, args.platform or default_platform())
    cfg = {
        "server": args.server.rstrip("/"),
        "device_token": data["device_token"],
        "device_id": data["device_id"],
        "device_name": args.name,
        "platform": args.platform or default_platform(),
    }
    save_config(cfg)
    print("Paired:", cfg["device_id"])
    print("Token saved to", "user config")


def cmd_run(args: argparse.Namespace) -> None:
    cfg = load_config()
    if not cfg.get("device_token"):
        raise SystemExit("Not paired. Run: python -m hermes_agent pair --server URL --code CODE --name NAME")
    client = HermesClient(cfg["server"], cfg["device_token"])
    print("Hermes agent running (Ctrl+C to stop)")
    while True:
        try:
            run_poll_loop(client)
        except Exception as exc:
            # Conexão instável (Windows/antivírus) — agente continua tentando.
            print("poll warning:", exc)
        time.sleep(args.interval)


def main() -> None:
    p = argparse.ArgumentParser(description="Hermes desktop agent (Linux / Windows / macOS / VPS)")
    sub = p.add_subparsers(dest="cmd", required=True)

    pp = sub.add_parser("pair", help="Pair this machine with the Hermes brain (VPS)")
    pp.add_argument("--server", required=True, help="https://your-vps.example.com")
    pp.add_argument("--code", required=True, help="Pairing code from panel/app")
    pp.add_argument("--name", required=True, help="Display name e.g. PC-Casa")
    pp.add_argument(
        "--platform",
        choices=["windows", "linux", "macos", "server"],
        default=None,
    )
    pp.set_defaults(func=cmd_pair)

    pr = sub.add_parser("run", help="Poll for commands")
    pr.add_argument("--interval", type=int, default=20)
    pr.set_defaults(func=cmd_run)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
