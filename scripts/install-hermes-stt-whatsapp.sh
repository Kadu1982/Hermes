#!/usr/bin/env bash
# STT para áudio WhatsApp no Hermes (faster-whisper local ou Groq/OpenAI)
set -euo pipefail

VENV="/usr/local/lib/hermes-agent/venv"
PY="$VENV/bin/python3"
CONFIG="${HOME}/.hermes/config.yaml"

echo "==> STT para áudio WhatsApp (Hermes)"

if [[ ! -x "$PY" ]]; then
  echo "ERRO: venv Hermes não encontrado em $VENV"
  exit 1
fi

if ! "$PY" -c "import faster_whisper" 2>/dev/null; then
  echo "    Instalando faster-whisper no venv Hermes..."
  if ! "$PY" -m pip --version &>/dev/null; then
    "$PY" -m ensurepip --upgrade || true
  fi
  "$PY" -m pip install -U faster-whisper
fi

"$PY" -c "from faster_whisper import WhisperModel; print('    faster-whisper OK')"

# Português BR para transcrição
if command -v python3 &>/dev/null && [[ -f "$CONFIG" ]]; then
  python3 <<'PY'
from pathlib import Path
import yaml

cfg = Path.home() / ".hermes" / "config.yaml"
data = yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
stt = data.setdefault("stt", {})
stt["enabled"] = True
stt.setdefault("provider", "local")
loc = stt.setdefault("local", {})
loc["model"] = loc.get("model") or "base"
loc["language"] = "pt"
cfg.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False), encoding="utf-8")
print("    config.yaml: stt.enabled=true, stt.local.language=pt")
PY
fi

systemctl restart hermes-gateway 2>/dev/null && echo "    hermes-gateway reiniciado" || true

echo ""
echo "==> Teste: envie um áudio curto no WhatsApp, ex.: «faz ping no PC-Casa»"
echo "    Alternativa cloud: descomente GROQ_API_KEY em ~/.hermes/.env e stt.provider: groq"
