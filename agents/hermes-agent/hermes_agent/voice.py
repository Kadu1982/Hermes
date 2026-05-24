"""Voz Jarvis — desktop (edge-tts no Linux; SAPI no Windows)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PROFILE_URL_SUFFIX = "/hermes/voice-profile"
_DEFAULT_PROFILE = {
    "display_name": "Jarvis",
    "edge_tts_voice": "pt-BR-AntonioNeural",
    "edge_tts_rate": "-8%",
    "edge_tts_pitch": "-4Hz",
    "speech_rate": 0.86,
    "ready_spoken": "Jarvis à sua disposição, senhor.",
    "task_done_spoken": "Concluído, senhor.",
    "task_failed_spoken": "Peço desculpas, senhor. Não foi possível concluir a operação.",
}


def load_local_profile() -> dict:
    for path in (
        Path(__file__).resolve().parents[3] / "shared" / "hermes_voice.json",
        Path(__file__).resolve().parents[1] / "hermes_voice.json",
    ):
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    return dict(_DEFAULT_PROFILE)


def speak_local(text: str, profile: dict | None = None) -> None:
    profile = profile or load_local_profile()
    if sys.platform == "darwin":
        rate = int(175 * float(profile.get("speech_rate", 0.86)))
        subprocess.run(["say", "-v", "Luca", "-r", str(rate), text], check=False)
        return
    if sys.platform == "win32":
        if _speak_edge_tts(text, profile):
            return
        ps = (
            "Add-Type -AssemblyName System.Speech; "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$s.Rate = -1; $s.Volume = 100; "
            f"$s.Speak({json.dumps(text)})"
        )
        subprocess.run(["powershell", "-Command", ps], check=False)
        return
    if _speak_edge_tts(text, profile):
        return
    print(f"Jarvis: {text}")


def _speak_edge_tts(text: str, profile: dict) -> bool:
    try:
        import edge_tts  # noqa: F401
    except ImportError:
        return False
    voice = profile.get("edge_tts_voice", "pt-BR-AntonioNeural")
    rate = profile.get("edge_tts_rate", "-8%")
    pitch = profile.get("edge_tts_pitch", "-4Hz")
    out = Path("/tmp/hermes_tts.mp3")
    cmd = [
        sys.executable,
        "-m",
        "edge_tts",
        "--voice",
        voice,
        f"--rate={rate}",
        f"--pitch={pitch}",
        "--text",
        text,
        "--write-media",
        str(out),
    ]
    if subprocess.run(cmd, check=False).returncode != 0:
        return False
    if sys.platform == "win32":
        subprocess.run(
            [
                "powershell",
                "-Command",
                f"(New-Object Media.SoundPlayer '{out}').PlaySync()",
            ],
            check=False,
        )
    else:
        subprocess.run(["ffplay", "-nodisp", "-autoexit", str(out)], check=False)
    return True
