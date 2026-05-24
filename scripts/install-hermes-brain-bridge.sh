#!/usr/bin/env bash
# Instala ponte cérebro Hermes (~/.hermes) → API jarvis-horizon (dispositivos).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/.env"
SKILL_SRC="$ROOT/shared/hermes-skills/jarvis-devices"
SKILL_DST="${HOME}/.hermes/skills/jarvis-devices"
CLI="$ROOT/scripts/jarvis_brain_cli.py"

echo "==> Jarvis brain bridge"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERRO: $ENV_FILE não encontrado"
  exit 1
fi

if ! grep -q '^HERMES_BRAIN_SERVICE_KEY=' "$ENV_FILE" 2>/dev/null; then
  KEY="$(openssl rand -hex 32)"
  echo "HERMES_BRAIN_SERVICE_KEY=$KEY" >> "$ENV_FILE"
  echo "    Chave de serviço gerada em .env"
else
  echo "    HERMES_BRAIN_SERVICE_KEY já existe"
fi

if ! grep -q '^HERMES_BRAIN_API_PUBLIC_URL=' "$ENV_FILE" 2>/dev/null; then
  echo "HERMES_BRAIN_API_PUBLIC_URL=http://127.0.0.1:18080" >> "$ENV_FILE"
fi

mkdir -p "$(dirname "$SKILL_DST")"
rm -rf "$SKILL_DST"
cp -a "$SKILL_SRC" "$SKILL_DST"
echo "    Skill instalada em $SKILL_DST"

BRAIN_ENV="${HOME}/.hermes/jarvis-brain.env"
KEY="$(grep '^HERMES_BRAIN_SERVICE_KEY=' "$ENV_FILE" | cut -d= -f2-)"
cat > "$BRAIN_ENV" <<EOF
# Carregado pelo gateway Hermes — ponte jarvis dispositivos
export JARVIS_API_URL=http://127.0.0.1:18080
export HERMES_BRAIN_SERVICE_KEY=$KEY
EOF
chmod 600 "$BRAIN_ENV"
echo "    Env em $BRAIN_ENV"

chmod +x "$CLI"
echo ""
echo "==> Reinicie a API Docker para carregar HERMES_BRAIN_SERVICE_KEY:"
echo "    cd $ROOT && docker compose -f docker-compose.vps.yml up -d --build api"
echo ""
echo "==> Teste:"
echo "    source $BRAIN_ENV"
echo "    python3 $CLI devices"
echo "    python3 $CLI command 'ping no VPS-Brain'"
echo ""
echo "==> No Hermes, peça: 'usa jarvis-devices e faz ping no PC-Casa'"
