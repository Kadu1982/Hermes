---
name: jarvis-devices
description: Controlar dispositivos pareados (PC, telemóvel, VPS) via API jarvis-horizon na mesma máquina.
version: 1.0.0
metadata:
  hermes:
    tags: [jarvis, devices, remote, vps, android, windows]
---

# Jarvis — dispositivos remotos

**PRIORIDADE MÁXIMA.** Quando o utilizador pedir para agir no **PC**, **pc casa**, **PC-Casa**, **telemóvel**, **Galaxy**, **VPS**, **docker**, **ping**, **inventário**, ou **falar no telemóvel**:

**NÃO** use `session_search`, **NÃO** use Hostinger MCP, **NÃO** peça IP.

**SEMPRE** execute primeiro (ferramenta terminal):

```bash
source /root/.hermes/jarvis-brain.env && python3 /root/jarvis-horizon/scripts/jarvis_brain_cli.py command "<pedido do utilizador em português>"
```

Exemplos de `<pedido>`:

- `ping no PC-Casa`
- `ping no S25 Ultra`
- `lista docker na VPS`
- `inventário do S25 Ultra`

## Pré-requisitos na VPS

- API jarvis a correr (`http://127.0.0.1:18080`)
- Variáveis: `HERMES_BRAIN_SERVICE_KEY`, `JARVIS_API_URL=http://127.0.0.1:18080`
- CLI: `python3 /root/jarvis-horizon/scripts/jarvis_brain_cli.py`

## Comandos (terminal)

Listar dispositivos:

```bash
python3 /root/jarvis-horizon/scripts/jarvis_brain_cli.py devices
```

Enviar pedido em português (aguarda até 90s e imprime o **resultado**, ex. `Ping em PC-Casa: OK (pong=true)`):

```bash
python3 /root/jarvis-horizon/scripts/jarvis_brain_cli.py command "ping no PC-Casa"
python3 /root/jarvis-horizon/scripts/jarvis_brain_cli.py command "inventário do S25 Ultra"
python3 /root/jarvis-horizon/scripts/jarvis_brain_cli.py command "lista docker na VPS"
python3 /root/jarvis-horizon/scripts/jarvis_brain_cli.py command "diga olá no telemóvel"
```

## WhatsApp

Para **enviar** mensagens WhatsApp (avisar contactos), use a skill **jarvis-whatsapp** (`hermes send --to whatsapp`).

## Regras

1. **Não** assumes que o comando já correu — executa o CLI e lê a resposta.
2. Menciona o **nome do dispositivo** como no painel: `PC-Casa`, `S25 Ultra`, `VPS-Brain`.
3. **Mostre ao utilizador a saída completa do CLI** (inclui pong true/false, lista docker, etc.) — não diga só «enviado».
4. Se falhar ou ficar pendente, sugere verificar agentes (`hermes_agent run` no PC, app no telemóvel, systemd na VPS).
5. O cérebro Hermes **planeja**; os dispositivos **executam** (mãos).

## Dispositivos típicos

| Nome | Plataforma | Exemplos |
|------|------------|----------|
| VPS-Brain | server | `server_docker_ps`, `server_disk`, `ping` |
| PC-Casa | windows | `ping`, `get_inventory`, `speak` |
| S25 Ultra | android | `ping`, `get_inventory`, `speak` |
