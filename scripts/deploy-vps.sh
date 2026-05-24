#!/usr/bin/env bash
# Deploy jarvis-horizon na VPS (stack isolado, sem saude_*)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

COMPOSE_FILE="docker-compose.vps.yml"
ENV_FILE="${ENV_FILE:-.env}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Crie $ENV_FILE a partir de .env.vps.example"
  exit 1
fi

# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a

echo "==> Projeto: jarvis-horizon (rede jarvis_horizon_net)"
echo "    API:   http://${VPS_PUBLIC_IP:-127.0.0.1}:${HERMES_API_HOST_PORT:-18080}"
echo "    Painel: http://${VPS_PUBLIC_IP:-127.0.0.1}:${HERMES_PANEL_HOST_PORT:-13000}"

docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" build
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d

echo "==> Aguardando API..."
for i in $(seq 1 60); do
  if curl -sf "http://127.0.0.1:${HERMES_API_HOST_PORT:-18080}/healthz" >/dev/null 2>&1; then
    echo "OK healthz"
    break
  fi
  sleep 2
  if [[ "$i" -eq 60 ]]; then
    echo "Timeout — ver logs: docker compose -f $COMPOSE_FILE logs api"
    exit 1
  fi
done

echo ""
echo "Deploy concluído."
echo "  Painel: http://${VPS_PUBLIC_IP}:${HERMES_PANEL_HOST_PORT:-13000}"
echo "  TOTP (primeiro boot): docker compose -f $COMPOSE_FILE logs api | grep otpauth"
