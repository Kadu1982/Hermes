# Napkin Runbook — jarvis-horizon

## Curation Rules
- Re-prioritize on every read.
- Keep recurring, high-value notes only.
- Max 10 items per category.
- Each item includes date + "Do instead".

## Product & Architecture (Highest Priority)
1. **[2026-05-19] SDD é a fonte da verdade**
   Do instead: antes de codar, ler `docs/SDD-HERMES-JARVIS-UNIFICADO.md` e validar contra invariantes INV-01..06.

2. **[2026-05-19] Um cérebro, muitos alvos**
   Do instead: não criar segundo LLM/gateway independente; usar conectores + API de dispositivos.

3. **[2026-05-19] Proveniência em comandos cruzados**
   Do instead: preencher `created_by_device_id` ou `created_by_user_id` e `write_audit()` em toda mutação.

## VPS / Runtime
1. **[2026-05-19] DNS na VPS**
   Do instead: se modelos falharem com `name resolution`, verificar `systemd-resolved` ou usar `/etc/resolv.conf` estático (8.8.8.8, 1.1.1.1).

2. **[2026-05-19] Hermes gateway vs agente do repo**
   Do instead: gateway em `~/.hermes` = cérebro LLM; `agents/hermes-agent` = cliente da API REST.

## Shell & Command Reliability
1. **[2026-05-19] Testes backend**
   Do instead: `cd backend && source ../.venv/bin/activate && PYTHONPATH=. pytest tests/ -q`
