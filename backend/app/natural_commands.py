from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import Device

# MVP: frases PT/EN → comando estruturado (LLM na VPS depois)
_PING = re.compile(r"\b(ping|teste|testar|conectividade)\b", re.I)
_INVENTORY = re.compile(r"\b(invent[aá]rio|inventory|status|informa[cç][aã]o)\b", re.I)
_UPLOAD = re.compile(r"\b(enviar|upload|mandar)\s+(arquivo|ficheiro|file)\b", re.I)
_SPEAK = re.compile(r"\b(diga|dizer|fale|falar|repete|repita|say|speak)\b", re.I)
_PHOTO = re.compile(r"\b(foto|fotografia|picture|image|imagem|captura|capturar|tirar|tira)\b", re.I)
_NAVIGATION = re.compile(
    r"\b(navega|navegar|navegação|navegacao|rota|dire[cç][aã]o|leva|levar|vai\s+para|ir\s+para|abre\s+(a\s+)?rota|abrir\s+rota|abrir\s+navega[cç][aã]o|me\s+leva|me\s+levar)\b",
    re.I,
)
_LOCATION = re.compile(
    r"\b(localiza[cç][aã]o|geolocaliza[cç][aã]o|gps|onde\s+(estou|estamos)|minha\s+localiza[cç][aã]o|manda\s+minha\s+localiza[cç][aã]o)\b",
    re.I,
)
_SEND_PHOTO = re.compile(r"\b(enviar|manda?r|compartilha?r|share)\s+(a\s+)?foto\b", re.I)
_GREETING = re.compile(r"\b(ol[aá]|oi|hello|hi|bom\s+dia|boa\s+noite)\b", re.I)
_SERVER = re.compile(r"\b(vps|servidor|server)\b", re.I)
_PHONE = re.compile(r"\b(telefone|phone|celular|galaxy|android|s25|telem[oó]vel)\b", re.I)
_PC = re.compile(r"\b(pc|computador|windows|casa|pc\s*casa)\b", re.I)
_DOCKER = re.compile(r"\b(docker|containers?|container)\b", re.I)


@dataclass
class ParsedNaturalCommand:
    device_id: uuid.UUID
    device_name: str
    type: str
    payload: dict | None
    confidence: str  # high | low


def _extract_speak_text(text: str) -> str:
    """Texto a falar no dispositivo alvo."""
    stripped = _SPEAK.sub("", text, count=1).strip()
    stripped = re.sub(r"^[,:\s\-]+", "", stripped)
    if stripped:
        return stripped[0].upper() + stripped[1:] if len(stripped) > 1 else stripped.upper()
    if _GREETING.search(text):
        return "Olá, senhor."
    return text.strip()


def _extract_navigation_destination(text: str) -> str:
    dest = text.strip()
    dest = re.sub(r"^(ei|oi|ok|hey)\s+(jarvis|hermes)[,:\-\s]*", "", dest, flags=re.I)
    dest = re.sub(
        r"^(me\s+)?(leva|levar|navega|navegar|abre|abrir|vai|ir|mostra|mostrar)\s+",
        "",
        dest,
        flags=re.I,
    )
    dest = re.sub(r"^(para|pra|pro|até|a|ao|à|em\s+direção\s+a)\s+", "", dest, flags=re.I)
    dest = re.sub(r"^(rota|navegação|navegacao)\s+(para|pra|pro|até|a)\s+", "", dest, flags=re.I)
    return dest.strip(" ,.:;-")


def resolve_device(db: Session, text: str, explicit_device_id: uuid.UUID | None) -> Device | None:
    if explicit_device_id:
        return db.get(Device, explicit_device_id)
    devices = db.query(Device).filter(Device.revoked_at.is_(None)).all()
    if not devices:
        return None
    lower = text.lower()
    for d in devices:
        if d.name.lower() in lower:
            return d
    if _SERVER.search(text):
        for d in devices:
            if d.platform in ("server", "linux") and "vps" in d.name.lower():
                return d
        for d in devices:
            if d.platform == "server":
                return d
    if _NAVIGATION.search(text):
        for d in devices:
            if d.platform == "android":
                return d
    if _PHONE.search(text):
        for d in devices:
            if d.platform == "android":
                return d
    if _PC.search(text) or re.search(r"\bcasa\b", text, re.I):
        for d in devices:
            if d.platform == "windows" and "casa" in d.name.lower():
                return d
        for d in devices:
            if d.platform == "windows":
                return d
    # "diga olá" sem destino → telemóvel Android (quem costuma falar)
    if _SPEAK.search(text) or _GREETING.search(text):
        for d in devices:
            if d.platform == "android":
                return d
    if len(devices) == 1:
        return devices[0]
    return None


def parse_natural_command(db: Session, text: str, explicit_device_id: uuid.UUID | None) -> ParsedNaturalCommand:
    text = text.strip()
    if not text:
        raise ValueError("Comando vazio")
    device = resolve_device(db, text, explicit_device_id)
    if device is None:
        raise ValueError(
            "Não encontrei o dispositivo. Menciona o nome (ex.: PC-Casa, S25 Ultra, VPS-Brain)."
        )
    if _PING.search(text):
        cmd_type, payload = "ping", None
    elif _INVENTORY.search(text):
        cmd_type, payload = "get_inventory", None
    elif _UPLOAD.search(text):
        cmd_type, payload = "request_upload", {}
    elif _NAVIGATION.search(text):
        destination = _extract_navigation_destination(text)
        if not destination:
            raise ValueError("Diz para onde queres navegar, por exemplo: 'me leva para casa'.")
        cmd_type, payload = "navigate_to", {"destination": destination, "mode": "driving"}
    elif _PHOTO.search(text):
        payload = {"archive_only": not bool(_SEND_PHOTO.search(text))}
        cmd_type = "take_photo"
    elif _LOCATION.search(text):
        cmd_type, payload = "get_location", {}
    elif _SPEAK.search(text) or (_GREETING.search(text) and not _PING.search(text)):
        cmd_type = "speak"
        payload = {"text": _extract_speak_text(text)}
    elif _DOCKER.search(text):
        cmd_type, payload = "server_docker_ps", None
    else:
        raise ValueError(
            "Não entendi o pedido. Exemplos: 'diga olá', 'ping no PC-Casa', "
            "'inventário do VPS', 'fale boa noite no telefone', "
            "'tira uma foto', 'onde estou', 'me leva para casa'."
        )
    return ParsedNaturalCommand(
        device_id=device.id,
        device_name=device.name,
        type=cmd_type,
        payload=payload,
        confidence="high",
    )
