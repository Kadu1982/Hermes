#!/usr/bin/env bash
# Evolution API na VPS + webhook para Hermes
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
ENV_FILE="$ROOT/.env.evolution"

echo "==> Evolution API (Jarvis)"
echo "    ATENÇÃO: não use o mesmo número no Hermes WhatsApp bridge e no Evolution."

if [[ ! -f "$ENV_FILE" ]]; then
  cp .env.evolution.example "$ENV_FILE"
  KEY="$(openssl rand -hex 32)"
  DBPW="$(openssl rand -hex 16)"
  sed -i "s/CHANGE_ME_openssl_rand_hex_32/$KEY/" "$ENV_FILE"
  sed -i "s/CHANGE_ME_db_password/$DBPW/" "$ENV_FILE"
  echo "    Criado $ENV_FILE com chaves geradas"
fi

# shellcheck source=/dev/null
source "$ENV_FILE"

docker compose -f docker-compose.evolution.yml --env-file "$ENV_FILE" up -d
echo "    Aguardando API..."
for i in $(seq 1 30); do
  if curl -sf "http://127.0.0.1:${EVOLUTION_HOST_PORT:-8085}" >/dev/null 2>&1; then
    echo "    Evolution API up"
    break
  fi
  sleep 2
done

"$ROOT/scripts/setup-whatsapp-jarvis.sh"

echo ""
echo "==> Próximos passos"
echo "  1) Manager: http://$(hostname -I | awk '{print $1}'):${EVOLUTION_HOST_PORT:-8085}/manager"
echo "  2) Criar instância: ${EVOLUTION_INSTANCE:-jarvis}"
echo "  3) Configurar webhook na instância → ${HERMES_WEBHOOK_URL:-http://127.0.0.1:8644/webhooks/jarvis-evolution}"
echo "  4) Docs: docs/WHATSAPP-EVOLUTION.md"
