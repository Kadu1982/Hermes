# Integração cérebro Hermes ↔ dispositivos Jarvis

## Arquitetura

```
Utilizador (WhatsApp / CLI hermes / Telegram)
        ↓
hermes gateway (~/.hermes)  ← cérebro LLM + skills
        ↓  jarvis_brain_cli.py  (X-Hermes-Brain-Key)
API jarvis-horizon :18080  /api/v1/brain/*
        ↓  fila de comandos
   VPS-Brain | PC-Casa | S25 Ultra
```

## Instalação na VPS

```bash
cd /root/jarvis-horizon
chmod +x scripts/install-hermes-brain-bridge.sh
./scripts/install-hermes-brain-bridge.sh
docker compose -f docker-compose.vps.yml up -d --build api
source ~/.hermes/jarvis-brain.env
python3 scripts/jarvis_brain_cli.py devices
python3 scripts/jarvis_brain_cli.py command "ping no PC-Casa"
```

## Skill Hermes

Copiada para `~/.hermes/skills/jarvis-devices/`. No chat:

> Lista os dispositivos jarvis e faz ping no PC-Casa.

O agente deve usar `jarvis_brain_cli.py` conforme a skill.

## Endpoints API (cérebro)

| Método | Path | Header |
|--------|------|--------|
| GET | `/api/v1/brain/status` | `X-Hermes-Brain-Key` |
| GET | `/api/v1/brain/devices` | `X-Hermes-Brain-Key` |
| POST | `/api/v1/brain/command` | `X-Hermes-Brain-Key` ou JWT admin |

Body `POST /brain/command`:

```json
{ "text": "inventário do S25 Ultra", "notify_channel": "silent" }
```

## Gateway 24h (opcional)

```bash
sudo cp deploy/hermes-gateway.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now hermes-gateway
```

Requer `hermes` no PATH (`~/.local/bin` ou venv).
