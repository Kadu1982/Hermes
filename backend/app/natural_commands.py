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
_OPEN_APP = re.compile(r"\b(abre|abrir|open|launch|inicia|iniciar|start)\b", re.I)
_UNLOCK = re.compile(r"\b(desbloqueia|desbloquear|destrava|destravar|unlock)\b", re.I)
_SYSTEM_ACTION_HOME = re.compile(r"\b(home|inicio|in[ií]cio|principal)\b", re.I)
_SYSTEM_ACTION_BACK = re.compile(r"\b(volta|voltar|back)\b", re.I)
_SYSTEM_ACTION_RECENTS = re.compile(r"\b(recents|recentes|apps\s+recentes|tarefas\s+recentes)\b", re.I)
_SYSTEM_ACTION_NOTIFICATIONS = re.compile(r"\b(notifica[cç][oõ]es?|alerts?|notificações?)\b", re.I)
_SYSTEM_ACTION_QUICK_SETTINGS = re.compile(r"\b(defini[cç][oõ]es\s+rápidas|defini[cç][oõ]es\s+rapidas|quick\s+settings|atalhos\s+rápidos|atalhos\s+rapidos)\b", re.I)
_DEEP_LINK_CAMERA = re.compile(r"\b(c[câ]mera|camera|fotografar|foto)\b", re.I)
_DEEP_LINK_MAPS = re.compile(r"\b(mapas?|maps|navega[cç][aã]o|navegação|navegacao|rota)\b", re.I)
_DEEP_LINK_SETTINGS = re.compile(r"\b(defini[cç][oõ]es|configura[cç][oõ]es|settings)\b", re.I)
_DEEP_LINK_PHONE = re.compile(r"\b(telefone|phone|chamada|ligar|discador|dialer)\b", re.I)
_APP_ALIASES = {
    "whatsapp": ("WhatsApp", "com.whatsapp"),
    "google maps": ("Google Maps", "com.google.android.apps.maps"),
    "maps": ("Google Maps", "com.google.android.apps.maps"),
    "chrome": ("Chrome", "com.android.chrome"),
    "google chrome": ("Chrome", "com.android.chrome"),
    "gmail": ("Gmail", "com.google.android.gm"),
    "telegram": ("Telegram", "org.telegram.messenger"),
    "settings": ("Settings", "com.android.settings"),
    "definições": ("Settings", "com.android.settings"),
    "configurações": ("Settings", "com.android.settings"),
    "camera": ("Camera", "com.android.camera2"),
    "câmera": ("Camera", "com.android.camera2"),
    "dialer": ("Phone", "com.google.android.dialer"),
    "phone": ("Phone", "com.google.android.dialer"),
}


def _strip_jarvis_prefix(text: str) -> str:
    return re.sub(r"^(ei|ok|hey)\s+(jarvis|hermes)[,:\-\s]*", "", text.strip(), flags=re.I)


def _normalize_android_phrase(text: str) -> str:
    text = _strip_jarvis_prefix(text)
    text = re.sub(r"\b(no|na|do|da|meu|minha|o|a|app|aplicativo|aplica[cç][aã]o|telefone|celular|telem[oó]vel|android|s25|galaxy)\b", " ", text, flags=re.I)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" ,.:;-")


def _extract_app_name(text: str) -> tuple[str, str | None]:
    normalized = _normalize_android_phrase(text)
    normalized = _OPEN_APP.sub("", normalized, count=1).strip()
    normalized = re.sub(r"^(o|a|um|uma|meu|minha)\s+", "", normalized, flags=re.I)
    for alias, (app_name, package_name) in _APP_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", normalized, re.I):
            return app_name, package_name
    app_name = normalized.strip(" ,.:;-")
    if not app_name:
        return "App", None
    return app_name[0].upper() + app_name[1:], None


def _extract_system_action(text: str) -> str | None:
    normalized = _normalize_android_phrase(text)
    if _SYSTEM_ACTION_HOME.search(normalized):
        return "home"
    if _SYSTEM_ACTION_BACK.search(normalized):
        return "back"
    if _SYSTEM_ACTION_RECENTS.search(normalized):
        return "recents"
    if _SYSTEM_ACTION_NOTIFICATIONS.search(normalized):
        return "notifications"
    if _SYSTEM_ACTION_QUICK_SETTINGS.search(normalized):
        return "quick_settings"
    return None


def _extract_deep_link_target(text: str) -> str | None:
    normalized = _normalize_android_phrase(text)
    if _DEEP_LINK_CAMERA.search(normalized):
        return "camera"
    if _DEEP_LINK_MAPS.search(normalized):
        return "maps"
    if _DEEP_LINK_SETTINGS.search(normalized):
        return "settings"
    if _DEEP_LINK_PHONE.search(normalized):
        return "phone"
    return None


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
    dest = re.sub(r"^(ei|oi|ok|hey)\s+(jarvis|hermes)[,:\-\s]*", "", text.strip(), flags=re.I)
    patterns = [
        r"^(?:me\s+)?(?:leva|levar|navega|navegar|abre|abrir|vai|ir|mostra|mostrar)\s+",
        r"^(?:rota|navegação|navegacao)\s+(?:para|pra|pro|até|a)\s+",
        r"^(?:para|pra|pro|até|a|ao|à|em\s+direção\s+a)\s+",
    ]
    for pattern in patterns:
        dest = re.sub(pattern, "", dest, flags=re.I)
    dest = re.sub(
        r"^(?:o|a|meu|minha)\s+(?:endereço|endereco|local|destino|rota|navegação|navegacao)\s+",
        "",
        dest,
        flags=re.I,
    )
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
    system_action = _extract_system_action(text)
    deep_link_target = _extract_deep_link_target(text)
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
    elif _UNLOCK.search(text):
        cmd_type, payload = "request_unlock", None
    elif system_action is not None:
        cmd_type, payload = "android_system_action", {"action": system_action}
    elif deep_link_target is not None and _OPEN_APP.search(text):
        cmd_type, payload = "android_deep_link", {"target": deep_link_target}
    elif _OPEN_APP.search(text):
        app_name, package_name = _extract_app_name(text)
        payload = {"app_name": app_name}
        if package_name is not None:
            payload["package_name"] = package_name
        cmd_type = "open_app"
    elif re.search(r"\b(app\s+ui|ui\s+action|ação\s+ui|acao\s+ui)\b", text, re.I):
        cmd_type, payload = "android_ui_action", {"flow": "allowlisted"}
    else:
        raise ValueError(
            "Não entendi o pedido. Exemplos: 'diga olá', 'ping no PC-Casa', "
            "'inventário do VPS', 'fale boa noite no telefone', "
            "'tira uma foto', 'onde estou', 'me leva para casa', "
            "'abre WhatsApp no telefone', 'volta para home no telefone', 'desbloqueia o telefone'."
        )
    return ParsedNaturalCommand(
        device_id=device.id,
        device_name=device.name,
        type=cmd_type,
        payload=payload,
        confidence="high",
    )
