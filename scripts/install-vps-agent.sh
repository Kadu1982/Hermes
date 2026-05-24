#!/usr/bin/env bash
# Instala o agente Hermes na VPS (host) para server_docker_ps, server_disk, ping.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AGENT_DIR="$ROOT/agents/hermes-agent"
VENV="$AGENT_DIR/.venv"
API_URL="${HERMES_API_URL:-http://127.0.0.1:18080}"

echo "==> API esperada: $API_URL"
echo "==> Criando venv em $VENV"
python3 -m venv "$VENV"
"$VENV/bin/pip" install -q -U pip
"$VENV/bin/pip" install -q -r "$AGENT_DIR/requirements.txt"

echo ""
echo "==> Próximo passo (manual):"
echo "  1. Painel http://72.60.55.213:13000 → Pairing → Generate"
echo "  2. Rode o pareamento:"
echo "     cd $AGENT_DIR"
echo "     $VENV/bin/python -m hermes_agent pair \\"
echo "       --server $API_URL \\"
echo "       --code CODIGO_DO_PAINEL \\"
echo "       --name VPS-Brain \\"
echo "       --platform server"
echo ""
echo "  3. Ativar serviço:"
echo "     sudo cp $ROOT/deploy/hermes-agent.service /etc/systemd/system/"
echo "     sudo systemctl daemon-reload"
echo "     sudo systemctl enable --now hermes-agent"
echo ""
echo "  4. Teste no painel: device VPS-Brain → server_docker_ps"
