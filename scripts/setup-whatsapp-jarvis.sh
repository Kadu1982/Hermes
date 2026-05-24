#!/usr/bin/env bash
# Configura skills WhatsApp + Jarvis no Hermes (~/.hermes)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HERMES_SKILLS="${HOME}/.hermes/skills"

echo "==> Skills Jarvis (WhatsApp + routing + devices)"
for skill in jarvis-routing jarvis-whatsapp jarvis-devices; do
  src="$ROOT/shared/hermes-skills/$skill"
  dst="$HERMES_SKILLS/$skill"
  if [[ ! -d "$src" ]]; then
    echo "ERRO: $src não encontrado"
    exit 1
  fi
  rm -rf "$dst"
  cp -a "$src" "$dst"
  echo "    $dst"
done

# Brain env para jarvis-devices
if [[ -x "$ROOT/scripts/install-hermes-brain-bridge.sh" ]]; then
  "$ROOT/scripts/install-hermes-brain-bridge.sh" 2>/dev/null | tail -3 || true
fi

echo ""
echo "==> WhatsApp no gateway"
if systemctl is-active hermes-gateway &>/dev/null; then
  echo "    hermes-gateway: active"
  hermes send --list whatsapp 2>/dev/null | head -5 || echo "    (liste com: hermes send --list whatsapp)"
else
  echo "    AVISO: hermes-gateway não está active — systemctl start hermes-gateway"
fi

echo ""
echo "==> Webhook Evolution (opcional)"
if command -v hermes &>/dev/null; then
  SECRET="${JARVIS_EVOLUTION_WEBHOOK_SECRET:-$(openssl rand -hex 24)}"
  hermes webhook subscribe jarvis-evolution \
    --prompt "Evento Evolution. Payload: {body}. Se houver pedido sobre PC, VPS, telemóvel ou docker, use jarvis-devices. Para enviar WhatsApp use jarvis-whatsapp." \
    --skills "jarvis-routing,jarvis-devices,jarvis-whatsapp" \
    --secret "$SECRET" 2>/dev/null && echo "    Webhook jarvis-evolution OK (secret guardado no subscription)" \
    || echo "    Webhook: já existe ou gateway precisa de plataforma webhook (porta 8644)"
  echo "    EVOLUTION_WEBHOOK_SECRET=$SECRET" >> "$ROOT/.env.evolution.example" 2>/dev/null || true
fi

echo ""
echo "==> System prompt + desativar Hostinger MCP para pedidos Jarvis"
python3 "$ROOT/scripts/patch-hermes-jarvis-prompt.py" || echo "    AVISO: patch prompt falhou (pip install pyyaml?)"
systemctl restart hermes-gateway 2>/dev/null && echo "    hermes-gateway reiniciado" || true

echo ""
echo "==> Testes sugeridos"
echo "  1) No WhatsApp: «Faz ping no PC-Casa»"
echo "  2) hermes send --to whatsapp \"Teste Jarvis\""
echo "  3) source ~/.hermes/jarvis-brain.env && python3 $ROOT/scripts/jarvis_brain_cli.py devices"
echo ""
echo "Docs: $ROOT/docs/WHATSAPP-ESTRATEGIA.md"
