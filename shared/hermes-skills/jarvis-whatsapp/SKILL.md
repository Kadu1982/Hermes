---
name: jarvis-whatsapp
description: Enviar e gerir WhatsApp pelo Hermes na VPS; combinar com jarvis-devices para controlar PC/VPS/telemóvel.
version: 1.0.0
metadata:
  hermes:
    tags: [whatsapp, messaging, jarvis, evolution]
---

# Jarvis — WhatsApp

## Enviar mensagem (Hermes nativo — preferido se o gateway WhatsApp estiver ligado)

Listar destinos:

```bash
hermes send --list whatsapp
```

Enviar:

```bash
hermes send --to whatsapp "Deploy terminou com sucesso."
hermes send --to "whatsapp:124618593542320@lid" "Mensagem para um chat específico"
```

## Pedidos do utilizador no WhatsApp

Quando alguém pedir no WhatsApp:

- ping / inventário / docker / falar no telemóvel / PC / VPS  
→ use a skill **jarvis-devices** e `jarvis_brain_cli.py` (não invente resultado).

Exemplos de pedido:

- «Faz ping no PC-Casa»
- «Inventário do S25 Ultra»
- «Lista docker na VPS»
- «Diz olá no telemóvel» (comando speak)

## Evolution API (se instalado)

Se existir `/root/jarvis-horizon/.env.evolution`:

```bash
source /root/jarvis-horizon/.env.evolution
curl -sS -X POST "http://127.0.0.1:8085/message/sendText/${EVOLUTION_INSTANCE}" \
  -H "apikey: ${EVOLUTION_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"number":"NUMERO_COM_DDI","text":"Sua mensagem"}'
```

Só use Evolution se o utilizador tiver migrado para Evolution (mesmo número **não** pode estar no bridge Hermes).

## Chamadas

- **Chamada WhatsApp (VoIP):** não suportado por API.
- **Chamada telefónica:** só via app Android (fase futura) ou pedir ao utilizador ligar manualmente.

## Idioma

Respostas ao utilizador em **português brasileiro**.
