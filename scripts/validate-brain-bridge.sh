#!/usr/bin/env bash
# Validação E2E: ponte cérebro Hermes ↔ API jarvis-horizon
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
FAIL=0
ok() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; FAIL=1; }

echo "========== Validação Hermes Brain Bridge =========="

echo "[1] Docker API"
if curl -sf http://127.0.0.1:18080/healthz >/dev/null; then
  ok "healthz"
else
  fail "healthz — API não responde em :18080"
fi

echo "[2] Import Python (commands.py)"
if grep -q 'get_current_admin' backend/app/routers/commands.py; then
  ok "get_current_admin importado"
else
  fail "get_current_admin em falta em commands.py"
fi

echo "[3] Brain env + install"
if [[ -f /root/.hermes/jarvis-brain.env ]]; then
  # shellcheck source=/dev/null
  source /root/.hermes/jarvis-brain.env
  ok "jarvis-brain.env"
else
  ./scripts/install-hermes-brain-bridge.sh
  source /root/.hermes/jarvis-brain.env
fi

if [[ -n "${HERMES_BRAIN_SERVICE_KEY:-}" ]]; then
  ok "HERMES_BRAIN_SERVICE_KEY definida"
else
  fail "chave cérebro vazia"
fi

echo "[4] Skill jarvis-devices"
if [[ -f /root/.hermes/skills/jarvis-devices/SKILL.md ]]; then
  ok "skill instalada"
else
  fail "skill em ~/.hermes/skills/jarvis-devices"
fi

echo "[5] CLI brain"
if python3 scripts/jarvis_brain_cli.py status | grep -q '"status": "ok"'; then
  ok "brain/status"
else
  fail "brain/status"
fi

if python3 scripts/jarvis_brain_cli.py devices | grep -q 'id='; then
  ok "brain/devices ($(python3 scripts/jarvis_brain_cli.py devices | wc -l) linhas)"
else
  fail "brain/devices — sem dispositivos"
fi

echo "[6] Comando natural (ping VPS-Brain)"
MSG=$(python3 scripts/jarvis_brain_cli.py command "ping no VPS-Brain" 2>&1) || true
if echo "$MSG" | grep -qiE 'ping|enviado|VPS'; then
  ok "brain/command: $MSG"
else
  fail "brain/command: $MSG"
fi

echo "[7] Auth negada sem chave"
CODE=$(curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:18080/api/v1/brain/status || echo 000)
if [[ "$CODE" == "401" ]]; then
  ok "401 sem X-Hermes-Brain-Key"
else
  fail "esperado 401 sem chave, obteve $CODE"
fi

echo "[8] OpenAPI /brain"
if curl -sf http://127.0.0.1:18080/openapi.json | grep -q '"/api/v1/brain/status"'; then
  ok "rotas brain no OpenAPI"
else
  fail "rotas brain no OpenAPI"
fi

echo "[9] systemd hermes-gateway"
if systemctl is-enabled hermes-gateway &>/dev/null; then
  ok "hermes-gateway enabled"
else
  echo "  WARN hermes-gateway não enabled ainda"
fi
if systemctl is-active hermes-gateway &>/dev/null; then
  ok "hermes-gateway active"
else
  echo "  WARN hermes-gateway não active (pode precisar auth gateway)"
fi

echo "========== Fim (FAIL=$FAIL) =========="
exit "$FAIL"
