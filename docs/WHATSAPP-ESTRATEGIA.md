# WhatsApp no Hermes Jarvis — Estratégia

## Resumo (recomendação)

| Camada | Função | Quando usar |
|--------|--------|-------------|
| **Hermes Gateway (VPS)** | Cérebro + WhatsApp já ligado (bridge Node/Baileys) | **Principal** — falar com Jarvis, pedir ping/PC/VPS, respostas com LLM |
| **Evolution API (VPS)** | REST + webhooks, painel, automações | **Opcional** — se quiser API HTTP, integrações externas, ou não usar o bridge Hermes |
| **App Android (S25)** | Mãos no telemóvel | **Complemento** — notificações, TTS, voz; **não** substitui API oficial do WhatsApp |

**Importante:** o mesmo número **não** pode estar ligado ao Hermes bridge **e** ao Evolution ao mesmo tempo. Escolha **um** conector de sessão WhatsApp.

---

## O que já funciona hoje (VPS)

- Gateway: `hermes-gateway.service` (ativo)
- WhatsApp: sessão em `~/.hermes/whatsapp/session`
- Exemplo de destino: `hermes send --list whatsapp`
- Dispositivos: skill `jarvis-devices` + `jarvis_brain_cli.py`

**Teste no WhatsApp:**  
> Faz ping no PC-Casa

O Hermes deve usar a skill `jarvis-devices` e o CLI na VPS.

---

## Evolution API (opcional)

Ver [WHATSAPP-EVOLUTION.md](WHATSAPP-EVOLUTION.md) e:

```bash
./scripts/install-evolution-vps.sh
```

Fluxo:

```
WhatsApp ↔ Evolution (Docker :8085) ↔ webhook ↔ Hermes (skill + cérebro)
                                      ↘ jarvis_brain_cli → dispositivos
```

Vantagens: REST estável, webhooks, múltiplas instâncias, painel.  
Desvantagem: outra stack Docker; **desliga** o WhatsApp nativo do Hermes se usar o mesmo número.

---

## App Android — o que é realista

| Pedido | Via app Hermes | Notas |
|--------|----------------|-------|
| Ler mensagens WhatsApp | 🟡 Fase 2 | `NotificationListener` — só texto das notificações, não histórico completo |
| Responder WhatsApp | 🟡 Fase 3 | Accessibility Service — frágil, pode quebrar com updates do WhatsApp |
| Chamadas WhatsApp (VoIP) | ❌ | Sem API pública; não é permissão de app |
| Chamadas telefónicas | 🟡 Fase 4 | `CALL_PHONE` + intent — chamada **celular**, não WhatsApp |
| Enviar WhatsApp | ✅ | Melhor pela **VPS** (Hermes ou Evolution), não pelo app |

O app continua como **agente do dispositivo** (ping, inventário, falar, voz). O **cérebro** manda WhatsApp pela VPS.

---

## Próximos passos

1. `./scripts/setup-whatsapp-jarvis.sh` — skills + instruções no Hermes  
2. Testar no WhatsApp: ping PC, inventário S25, mensagem para contacto  
3. (Opcional) Evolution se quiser API REST dedicada  
4. Android: fases em [WHATSAPP-ANDROID-FASES.md](WHATSAPP-ANDROID-FASES.md)
