# AGENTS.md — Hermes / Jarvis Unificado

Instruções para agentes de código (Cursor, Codex, Hermes CLI) trabalhando neste repositório.

## Fonte da verdade

Leia e siga o **[SDD formal](docs/SDD-HERMES-JARVIS-UNIFICADO.md)** antes de implementar qualquer módulo.

Definição curta:

> Um único Hermes central, com qualquer dispositivo podendo acionar qualquer outro, mantendo contexto persistente, execução contínua, roteamento por intenção e integração com código, e-mail, WhatsApp e dispositivos.

## Perguntas obrigatórias por mudança

1. Isso reforça o **agente único** (não cria outro cérebro)?
2. Isso preserva **roteamento entre dispositivos** com proveniência?
3. Isso mantém **contexto e continuidade** de tarefas?
4. Isso respeita **Jarvis central** (celular = interface)?
5. Isso adiciona ou preserva **auditoria/logs**?

## Layout do monorepo

| Path | Papel |
|------|-------|
| `backend/` | API FastAPI — dispositivos, comandos, auditoria |
| `panel/` | Painel admin Next.js |
| `android/` | App Android (agente + Comando) |
| `agents/hermes-agent/` | Agente desktop/VPS |
| `docs/SDD-HERMES-JARVIS-UNIFICADO.md` | SDD — não contradizer |

## Runtime na VPS (fora deste repo)

- Cérebro conversacional: `hermes gateway run` (`~/.hermes/`)
- WhatsApp, LLM, skills: configurados em `~/.hermes/config.yaml`

Não confundir o **Hermes Agent upstream** (`/usr/local/lib/hermes-agent`) com o **agente leve** deste repo (`agents/hermes-agent/`), que consome a API REST.

## Convenções

- Comandos entre dispositivos: registrar `created_by_user_id` ou `created_by_device_id`.
- Mutações sensíveis: chamar `write_audit()`.
- Escopo mínimo nas PRs; não expandir além do SDD sem alinhamento.
