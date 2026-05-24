from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
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


def _segment_after(text: str, marker: str, stop_markers: tuple[str, ...] = ()) -> str:
    lower = text.lower()
    idx = lower.find(marker.lower())
    if idx < 0:
        return ""
    start = idx + len(marker)
    tail = text[start:]
    lower_tail = lower[start:]
    end = len(tail)
    for stop in stop_markers:
        stop_idx = lower_tail.find(stop.lower())
        if stop_idx >= 0:
            end = min(end, stop_idx)
    return tail[:end].strip(" ,;:-")


def _calendar_datetime_range(text: str) -> tuple[str, str]:
    now = datetime.now().astimezone()
    lower = text.lower()
    delta_days = 0
    if "depois de amanhã" in lower or "depois de amanha" in lower:
        delta_days = 2
    elif "amanhã" in lower or "amanha" in lower:
        delta_days = 1

    date_match = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{4}))?\b", lower)
    if date_match:
        day = int(date_match.group(1))
        month = int(date_match.group(2))
        year = int(date_match.group(3) or now.year)
        target_date = datetime(year, month, day, tzinfo=now.tzinfo).date()
    else:
        target_date = (now + timedelta(days=delta_days)).date()

    time_match = re.search(r"\b(?:às|as)?\s*(\d{1,2})(?::(\d{2}))?\s*h?\b", lower)
    hour = int(time_match.group(1)) if time_match else 9
    minute = int(time_match.group(2) or 0) if time_match else 0
    start = datetime(target_date.year, target_date.month, target_date.day, hour, minute, tzinfo=now.tzinfo)

    duration_minutes = 30 if "meia hora" in lower or "30 minutos" in lower else 60
    if "2 horas" in lower or "duas horas" in lower:
        duration_minutes = 120
    end = start + timedelta(minutes=duration_minutes)
    return start.isoformat(), end.isoformat()


def route_google_natural(text: str) -> RoutedGoogleAction:
    raw = text.strip()
    if not raw:
        raise ValueError("Comando vazio")

    lower = raw.lower()
    confirmation_required = bool(_DELETE.search(raw) or _SHARE.search(raw))

    if _GMAIL.search(raw):
        if _CREATE.search(raw) or any(term in lower for term in ["enviar", "send", "mandar", "mande", "envie", "responder", "reply"]):
            to = _segment_after(raw, "para", (" assunto", " sobre", " com assunto", " dizendo", " diga ", " mensagem", " texto", " corpo"))
            subject = _segment_after(raw, "assunto", (" e mensagem", " mensagem", " e texto", " texto", " e corpo", " corpo", " dizendo", " sobre"))
            body = _segment_after(raw, "mensagem", (" assunto",))
            if not body:
                body = _segment_after(raw, "texto", (" assunto",))
            if not body:
                body = _segment_after(raw, "corpo", (" assunto",))
            if not body:
                body = _segment_after(raw, "dizendo", ())
            if not body:
                body = _strip_helpers(raw)
            if not subject:
                subject = "Mensagem do Hermes"
            if not to:
                to = _segment_after(raw, "pro", (" assunto", " sobre", " mensagem", " texto", " corpo"))
            action = "send"
            params: dict[str, Any] = {
                "to": to,
                "subject": subject,
                "body": body,
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
        if _CREATE.search(raw) or any(term in lower for term in ["marque", "agende", "agenda", "marcar", "agendar"]):
            start, end = _calendar_datetime_range(raw)
            summary = _segment_after(raw, "criar", (" amanhã", " amanha", " hoje", " às", " as "))
            if not summary:
                summary = _segment_after(raw, "agendar", (" amanhã", " amanha", " hoje", " às", " as "))
            if not summary:
                summary = _segment_after(raw, "marcar", (" amanhã", " amanha", " hoje", " às", " as "))
            if not summary:
                summary = _segment_after(raw, "agende", (" amanhã", " amanha", " hoje", " às", " as "))
            if not summary:
                summary = _segment_after(raw, "marque", (" amanhã", " amanha", " hoje", " às", " as "))
            if not summary:
                summary = raw
            return RoutedGoogleAction(
                "calendar",
                "create",
                {"summary": summary, "start": start, "end": end, "calendar": "primary"},
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
