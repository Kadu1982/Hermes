# Hermes Agent (Linux / Windows / macOS / VPS)

Lightweight agent for desktops and servers. Same API as the Android app (agent role).

## Install

```bash
cd agents/hermes-agent
pip install -r requirements.txt
```

## Pair (once per machine)

Generate a code in the Hermes panel (**Pairing**), then:

```bash
python -m hermes_agent pair \
  --server https://YOUR_VPS_HOST \
  --code AB12CD34 \
  --name "PC-Casa" \
  --platform windows
```

Platforms: `windows`, `linux`, `macos`, `server` (use `server` for the VPS itself).

## Run agent

```bash
python -m hermes_agent run --interval 20
```

Keep running in background (systemd, Windows Task Scheduler, or `launchd` on Mac).

**Windows:** see [docs/WINDOWS_AGENT.md](../../docs/WINDOWS_AGENT.md) — `scripts/run-agent.bat` + `scripts/install-task-scheduler.ps1`.

## VPS as a device

On the VPS where Docker/API runs:

```bash
python -m hermes_agent pair --server https://localhost_OR_PUBLIC_URL --code ... --name "VPS-Brain" --platform server
python -m hermes_agent run
```

Commands: `server_docker_ps`, `server_disk`, `ping`, `get_inventory`.

## Voice

Desktop agents use the same [hermes_voice.json](../../shared/hermes_voice.json) profile as the mobile app (optional `edge-tts` on Linux).
