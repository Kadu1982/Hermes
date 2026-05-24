# TODO / Roadmap — Hermes Jarvis Unificado

Última atualização: 2026-05-19 (validação E2E na VPS — `scripts/validate-brain-bridge.sh` FAIL=0)

Legenda: ✅ Feito · 🟡 Parcial · ⬜ Por fazer · 🔴 Bloqueado

---

## 1. Infraestrutura VPS (24h online)

| # | Necessidade | Estado | Notas |
|---|-------------|--------|-------|
| 1.1 | API + Postgres + painel Docker (`18080` / `13000`) | ✅ | `docker-compose.vps.yml` |
| 1.2 | DNS / HTTPS com domínio | ⬜ | Hoje HTTP + IP |
| 1.3 | Firewall só portas necessárias | 🟡 | Documentado em `DEPLOY_VPS.md` |
| 1.4 | Backup Postgres | ⬜ | |
| 1.5 | `hermes gateway` systemd 24h | ✅ | `hermes-gateway` enabled + active na VPS |

---

## 2. Cérebro Hermes (Nous, `~/.hermes`)

| # | Necessidade | Estado | Notas |
|---|-------------|--------|-------|
| 2.1 | Hermes Agent instalado na VPS | ✅ | `/root/.hermes` |
| 2.2 | Modelo LLM configurado (Codex/OpenRouter) | 🟡 | Verificar `auth.json` / DNS |
| 2.3 | **Ponte cérebro → API dispositivos** | ✅ | Validado: status, devices, ping VPS-Brain, 401 sem chave |
| 2.4 | Skill `jarvis-devices` em `~/.hermes/skills` | ✅ | `~/.hermes/skills/jarvis-devices/SKILL.md` |
| 2.5 | WhatsApp / Telegram no gateway | 🟡 | WhatsApp ligado (bridge); skills `jarvis-whatsapp` + routing; Evolution opcional |
| 2.6 | Comandos 100% linguagem natural via LLM (sem só regex) | ⬜ | Próximo: tool nativa ou MCP na API |
| 2.7 | Memória unificada (projetos, preferências) | 🟡 | Existe em `~/.hermes`; não ligada à auditoria jarvis |

---

## 3. Dispositivos (mãos)

| # | Necessidade | Estado | Notas |
|---|-------------|--------|-------|
| 3.1 | VPS-Brain pareado + agente | ✅ | `VPS-Brain`, systemd opcional |
| 3.2 | PC-Casa Windows pareado + agente | 🟡 | Pair OK; Task Scheduler `HermesAgent` |
| 3.3 | S25 Ultra pareado + app agente | ✅ | Ping / inventário OK |
| 3.4 | Comando `speak` (TTS) | ✅ | Android + desktop |
| 3.5 | Comando `server_docker_ps` | ✅ | VPS-Brain |
| 3.6 | Upload / download ficheiros | ⬜ | API existe; E2E pendente |
| 3.7 | Revogar / re-pair E2E | ⬜ | Testes 9–10 checklist |

---

## 4. App Android

| # | Necessidade | Estado | Notas |
|---|-------------|--------|-------|
| 4.1 | Pareamento (`18080`) | ✅ | |
| 4.2 | Aba Comando + login admin + 2FA | 🟡 | Reset TOTP; sessão 7 dias |
| 4.3 | Comandos naturais (`diga olá`, `ping`) | ✅ | Parser API + `speak` |
| 4.4 | Voz masculina Jarvis | 🟡 | Rebuild + Google TTS masculino |
| 4.5 | Modo «Ei Jarvis» (estilo Alexa) | 🟡 | `VoiceWakeForegroundService`; rebuild |
| 4.6 | Sincronizar código PC ↔ repositório VPS | ⬜ | `App-Hermes` no Windows desatualizado |
| 4.7 | Push FCM ao concluir comando | ⬜ | Fora do MVP |

---

## 5. Painel web

| # | Necessidade | Estado | Notas |
|---|-------------|--------|-------|
| 5.1 | Login + 2FA | ✅ | `admin@example.com` |
| 5.2 | Pairing + lista dispositivos | ✅ | |
| 5.3 | Enviar comandos por dispositivo | ✅ | |
| 5.4 | Auditoria | 🟡 | Página existe; validar conteúdo |
| 5.5 | UI comando natural (texto livre) | ⬜ | Só no app Android hoje |

---

## 6. Segurança e operação

| # | Necessidade | Estado | Notas |
|---|-------------|--------|-------|
| 6.1 | 2FA admin | ✅ | Google Authenticator |
| 6.2 | Chave cérebro (`HERMES_BRAIN_SERVICE_KEY`) | ✅ | Em `.env` + `~/.hermes/jarvis-brain.env` |
| 6.3 | HTTPS / não expor Postgres | ✅ | Postgres interno |
| 6.4 | Rotação tokens dispositivo | ⬜ | Endpoint existe |

---

## 7. Experiência «um Jarvis só»

| # | Necessidade | Estado | Notas |
|---|-------------|--------|-------|
| 7.1 | Um cérebro na VPS controla os 3 dispositivos | ✅ | CLI + gateway 24h; agentes PC/S25 dependem de poll |
| 7.2 | Celular como interface, não como cérebro | ✅ | SDD |
| 7.3 | Voz no telemóvel sem abrir app (Alexa) | 🟡 | MVP escuta contínua |
| 7.4 | Falar com Jarvis no WhatsApp e mandar no PC | 🟡 | Gateway ativo; testar «ping no PC-Casa» no WhatsApp |
| 7.5 | Contexto: «continua o deploy no PC» entre sessões | ⬜ | Memória Hermes + auditoria |

---

## Próximos 5 passos recomendados

1. ~~**VPS:** bridge + validate~~ ✅ (`bash scripts/validate-brain-bridge.sh`)
2. ~~**VPS:** `hermes-gateway` systemd~~ ✅
3. **PC:** Sincronizar `hermes-agent` + `client.py` + Task Scheduler.
4. **Telemóvel:** Rebuild app (voz Jarvis + Ei Jarvis + fix login).
5. **E2E:** Painel ou CLI cérebro → `ping` nos 3 dispositivos na mesma sessão.

---

## Referências

- [SDD](SDD-HERMES-JARVIS-UNIFICADO.md)
- [Deploy VPS](DEPLOY_VPS.md)
- [Integração cérebro](INTEGRACAO_CEREBRO.md)
- [Voz Jarvis](VOZ_JARVIS.md)
- [Modo Alexa](VOZ_ALEXA.md)
- [Testes E2E](TESTES_E2E.md)
