from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


_GMAIL = re.compile(r"\b(gmail|e-?mails?|correio|mails?|mensagem(?:ns)?)\b", re.I)
_CALENDAR = re.compile(r"\b(calendar|agenda|reuni[aã]o|compromisso|evento)\b", re.I)
_DRIVE = re.compile(r"\b(drive|arquivo(?:s)?|pasta(?:s)?)\b", re.I)
_DOCS = re.compile(r"\b(docs?|documento(?:s)?)\b", re.I)
_SHEETS = re.compile(r"\b(sheets?|planilha(?:s)?)\b", re.I)

_SEARCH = re.compile(r"\b(busca|buscar|procurar|pesquisar|search|find|listar|listar|ver|mostrar)\b", re.I)
_CREATE = re.compile(r"\b(criar|nova|novo|agendar|marcar|enviar|send|salvar)\b", re.I)
_DELETE = re.compile(r"\b(apagar|deletar|remover|excluir|delete)\b", re.I)
_SHARE = re.compile(r"\b(compartilhar|share|partilhar)\b", re.I)
_UPLOAD = re.compile(r"\b(enviar|upload|carregar)\b", re.I)
_DOWNLOAD = re.compile(r"\b(baixar|download|exportar)\b", re.I)


@dataclass(frozen=True)
class RoutedGoogleAction:
    service: str
    action: str
    params: dict[str, Any]
    confidence: str
    confirmation_required: bool
    confirmation_text: str | None = None


def _strip_helpers(text: str) -> str:
    cleaned = text
    cleaned = re.sub(r"\b(google|g-suite|workspace|hermes|jarvis)\b", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _gmail_query(text: str) -> str:
    lower = text.lower()
    query_parts = []
    if any(term in lower for term in ["não lidos", "nao lidos", "unread", "inbox"]):
        query_parts.append("is:unread")
    if any(term in lower for term in ["hoje", "today"]):
        query_parts.append("newer_than:1d")
    if any(term in lower for term in ["ontem", "yesterday"]):
        query_parts.append("newer_than:2d")
    free_text = _strip_helpers(text)
    free_text = re.sub(r"\b(gmail|e-?mails?|correio|mails?|mensagem(?:ns)?|buscar|procurar|pesquisar|ver|mostrar|listar)\b", "", free_text, flags=re.I)
    free_text = re.sub(r"\s+", " ", free_text).strip()
    if free_text:
        query_parts.append(free_text)
    return " ".join(query_parts) or "in:inbox"


def route_google_natural(text: str) -> RoutedGoogleAction:
    raw = text.strip()
    if not raw:
        raise ValueError("Comando vazio")

    lower = raw.lower()
    confirmation_required = bool(_DELETE.search(raw) or _SHARE.search(raw))

    if _GMAIL.search(raw):
        if _CREATE.search(raw) or any(term in lower for term in ["enviar", "send", "responder", "reply"]):
            action = "send"
            params: dict[str, Any] = {
                "to": "",
                "subject": "",
                "body": raw,
            }
            confidence = "low"
        elif _SEARCH.search(raw) or any(term in lower for term in ["não lidos", "nao lidos", "unread"]):
            action = "search"
            params = {"query": _gmail_query(raw), "max": 10}
            confidence = "high"
        elif _DELETE.search(raw):
            action = "modify"
            params = {"message_id": "", "remove_labels": "UNREAD"}
            confidence = "low"
            confirmation_required = True
        else:
            action = "search"
            params = {"query": _gmail_query(raw), "max": 10}
            confidence = "medium"
        return RoutedGoogleAction("gmail", action, params, confidence, confirmation_required)

    if _CALENDAR.search(raw):
        if _DELETE.search(raw):
            return RoutedGoogleAction(
                "calendar",
                "delete",
                {"event_id": "", "calendar": "primary"},
                "low",
                True,
            )
        if _CREATE.search(raw):
            return RoutedGoogleAction(
                "calendar",
                "create",
                {"summary": raw, "start": "", "end": "", "calendar": "primary"},
                "low",
                False,
            )
        return RoutedGoogleAction(
            "calendar",
            "list",
            {"calendar": "primary", "max": 25},
            "high",
            False,
        )

    if _DRIVE.search(raw):
        if _DELETE.search(raw):
            return RoutedGoogleAction(
                "drive",
                "delete",
                {"file_id": "", "permanent": False},
                "low",
                True,
            )
        if _SHARE.search(raw):
            return RoutedGoogleAction(
                "drive",
                "share",
                {"file_id": "", "type": "user", "role": "reader", "notify": False},
                "low",
                True,
            )
        if _UPLOAD.search(raw):
            return RoutedGoogleAction(
                "drive",
                "upload",
                {"path": "", "name": "", "parent": ""},
                "low",
                False,
            )
        if _DOWNLOAD.search(raw):
            return RoutedGoogleAction(
                "drive",
                "download",
                {"file_id": "", "output": "", "export_mime": ""},
                "low",
                False,
            )
        return RoutedGoogleAction(
            "drive",
            "search",
            {"query": _strip_helpers(raw), "max": 10, "raw_query": False},
            "medium",
            False,
        )

    if _DOCS.search(raw):
        if _CREATE.search(raw):
            return RoutedGoogleAction(
                "docs",
                "create",
                {"title": raw, "body": ""},
                "low",
                False,
            )
        if _DELETE.search(raw):
            return RoutedGoogleAction(
                "docs",
                "append",
                {"doc_id": "", "text": raw},
                "low",
                True,
            )
        return RoutedGoogleAction(
            "docs",
            "get",
            {"doc_id": ""},
            "low",
            False,
        )

    if _SHEETS.search(raw):
        if _CREATE.search(raw):
            return RoutedGoogleAction(
                "sheets",
                "create",
                {"title": raw, "sheet_name": ""},
                "low",
                False,
            )
        if _DELETE.search(raw) or "editar" in lower or "edit" in lower:
            return RoutedGoogleAction(
                "sheets",
                "update",
                {"sheet_id": "", "range": "Sheet1!A1", "values": [[]]},
                "low",
                True,
            )
        return RoutedGoogleAction(
            "sheets",
            "get",
            {"sheet_id": "", "range": "Sheet1!A1:A10"},
            "low",
            False,
        )

    raise ValueError(
        "Não consegui identificar uma ação do Google. Tente mencionar Gmail, Calendar, Drive, Docs ou Sheets."
    )
