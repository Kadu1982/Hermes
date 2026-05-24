# WhatsApp via App Android — Fases

O app Hermes no S25 **não** controla o WhatsApp como o Evolution/Hermes na VPS. Estas fases são complementares.

## Fase 1 (atual) — Agente Jarvis

- Poll de comandos: `ping`, `get_inventory`, `speak`
- Voz «Ei Jarvis» → API natural commands
- Sem acesso ao WhatsApp

## Fase 2 — Ler notificações

- Permissão: `BIND_NOTIFICATION_LISTENER_SERVICE`
- Comando API: `get_notification_inbox` (planeado)
- Lê **pré-visualizações** de notificações (WhatsApp, SMS, etc.)
- Limitações: sem histórico antigo; texto pode estar truncado

## Fase 3 — Responder (Accessibility)

- `AccessibilityService` para automatizar UI do WhatsApp
- Frágil; pode violar termos de uso; só se o utilizador aceitar risco
- Comando: `android_ui_action` com confirmação

## Fase 4 — Chamadas celulares

- `CALL_PHONE` + intent `tel:` — **não** é chamada WhatsApp
- Comando: `place_call` com confirmação no ecrã

## Recomendação

Para «ler/responder WhatsApp» e avisar contactos: use **Hermes na VPS** (já ligado) ou **Evolution API**.

Use o **telefone** para: voz, sensores, inventário, ficheiros, notificações locais.
