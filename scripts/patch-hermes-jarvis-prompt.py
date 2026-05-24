#!/usr/bin/env python3
"""Injeta regras Jarvis no system_prompt do Hermes e desativa MCP Hostinger para não roubar pedidos de dispositivos."""
from __future__ import annotations

import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Instale PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

CONFIG = Path.home() / ".hermes" / "config.yaml"
MARKER_START = "# === JARVIS_DEVICES_START ==="
MARKER_END = "# === JARVIS_DEVICES_END ==="

JARVIS_BLOCK = r"""
# === JARVIS_DEVICES_START ===
# Dispositivos Jarvis (jarvis-horizon) — OBRIGATÓRIO no WhatsApp e CLI

Quando o utilizador pedir QUALQUER ação em: PC, pc casa, PC-Casa, computador, Windows, VPS, servidor,
docker, containers, telemóvel, celular, S25, Galaxy, ping, inventário, falar no telemóvel:

1) PRIMEIRA ação: ferramenta **terminal** (nunca session_search, nunca Hostinger MCP para isto):
   source /root/.hermes/jarvis-brain.env && python3 /root/jarvis-horizon/scripts/jarvis_brain_cli.py command "<pedido em português>"

2) Nomes exatos dos dispositivos já pareados: **PC-Casa**, **S25 Ultra**, **VPS-Brain**.
   "pc casa" = PC-Casa. NÃO peça IP nem hostname.

3) Docker na VPS do utilizador = comando natural "lista docker na VPS" via jarvis_brain_cli (agente VPS-Brain),
   NÃO use painel Hostinger nem API Hostinger para listar Docker.

4) Só depois de executar o CLI, responda com a saída COMPLETA do terminal (ex.: «Ping em PC-Casa: OK (pong=true)»). Nunca diga apenas «enviado».

5) Skills: jarvis-devices, jarvis-routing, jarvis-whatsapp.
# === JARVIS_DEVICES_END ===
""".strip()


def main() -> None:
    if not CONFIG.exists():
        print(f"ERRO: {CONFIG} não encontrado", file=sys.stderr)
        sys.exit(1)

    data = yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}
    agent = data.setdefault("agent", {})
    sp = agent.get("system_prompt") or ""

    if MARKER_START in sp:
        # replace existing block
        before = sp.split(MARKER_START)[0].rstrip()
        after = sp.split(MARKER_END)[-1].lstrip() if MARKER_END in sp else ""
        agent["system_prompt"] = f"{before}\n\n{JARVIS_BLOCK}\n\n{after}".strip()
        print("Bloco JARVIS atualizado no system_prompt")
    else:
        agent["system_prompt"] = f"{sp.rstrip()}\n\n{JARVIS_BLOCK}".strip()
        print("Bloco JARVIS adicionado ao system_prompt")

    # WhatsApp: prompt por DM (self-chat / utilizador)
    wa = data.setdefault("whatsapp", {})
    if not isinstance(wa, dict):
        wa = {}
        data["whatsapp"] = wa
    prompts = wa.setdefault("channel_prompts", {})
    if not isinstance(prompts, dict):
        prompts = {}
        wa["channel_prompts"] = prompts
    default_prompt = (
        "Canal WhatsApp Jarvis. Para PC-Casa, S25 Ultra, VPS-Brain, ping, docker ou inventário: "
        "execute SEMPRE jarvis_brain_cli via terminal antes de responder. Não use Hostinger MCP."
    )
    if "*" not in prompts and not prompts:
        prompts["*"] = default_prompt
        print("channel_prompts[*] WhatsApp definido")
    elif prompts.get("*") != default_prompt:
        prompts["*"] = default_prompt
        print("channel_prompts[*] WhatsApp atualizado")

    # Desativar Hostinger MCP (confunde docker/VPS com Jarvis local)
    mcp = data.get("mcp_servers") or {}
    if "hostinger_mcp" in mcp:
        mcp["hostinger_mcp_disabled"] = mcp.pop("hostinger_mcp")
        data["mcp_servers"] = mcp
        print("hostinger_mcp movido para hostinger_mcp_disabled")

    CONFIG.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False), encoding="utf-8")
    print(f"OK: {CONFIG}")


if __name__ == "__main__":
    main()
