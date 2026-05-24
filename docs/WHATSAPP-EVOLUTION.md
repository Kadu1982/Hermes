# Evolution API + Hermes Jarvis

## Pré-requisitos

- VPS com Docker
- **Não** ter o mesmo número ligado ao bridge Hermes (`hermes gateway` WhatsApp) ao mesmo tempo

## Instalação

```bash
cd /root/jarvis-horizon
chmod +x scripts/install-evolution-vps.sh
./scripts/install-evolution-vps.sh
```

## Portas

| Serviço | Porta |
|---------|-------|
| Evolution API | `8085` → container `8080` |
| Hermes webhook (se ativo) | `8644` |

## Criar instância e QR

1. Abra `http://72.60.55.213:8085/manager` (ou via API)
2. Crie instância `jarvis`
3. Escaneie o QR com o telemóvel

## Webhook → Hermes

O script `install-evolution-vps.sh` regista webhook na Evolution apontando para o adaptador local, que reencaminha para o Hermes (`/webhooks/jarvis-evolution`).

Variáveis em `.env.evolution`:

- `EVOLUTION_API_KEY` — chave da API
- `EVOLUTION_INSTANCE=jarvis`
- `HERMES_WEBHOOK_URL=http://127.0.0.1:8644/webhooks/jarvis-evolution`

## Enviar mensagem (REST)

```bash
source /root/jarvis-horizon/.env.evolution
curl -sS -X POST "http://127.0.0.1:8085/message/sendText/${EVOLUTION_INSTANCE}" \
  -H "apikey: ${EVOLUTION_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"number":"5511999999999","text":"Olá do Jarvis"}'
```

## Skill Hermes

`~/.hermes/skills/jarvis-whatsapp/` — envio via `hermes send` ou curl Evolution.
