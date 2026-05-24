from __future__ import annotations

import pytest

from app.google_natural import route_google_natural
from app.google_workspace import GoogleWorkspaceError, GoogleWorkspaceResult, build_command, is_destructive, run


def test_google_workspace_build_command_for_drive_delete():
    cmd = build_command("drive", "delete", {"file_id": "file-123", "permanent": False}, confirm=True)
    assert cmd[:3] == [
        "/root/.hermes/google-venv/bin/python",
        "/root/.hermes/skills/productivity/google-workspace/scripts/google_api.py",
        "drive",
    ]
    assert "--confirm" in cmd
    assert "delete" in cmd
    assert "file-123" in cmd


def test_google_workspace_requires_confirmation_for_destructive_action():
    assert is_destructive("drive", "delete")
    with pytest.raises(GoogleWorkspaceError, match="requires confirm=true"):
        run("drive", "delete", {"file_id": "file-123"}, confirm=False)


def test_google_workspace_route_returns_summary(client, admin_user, monkeypatch):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": admin_user["email"], "password": admin_user["password"]},
    )
    tok = login.json()["access_token"]
    tfa = client.post(
        "/api/v1/auth/2fa/verify",
        json={"access_token": tok, "code": admin_user["code"]},
    )
    admin_tok = tfa.json()["access_token"]

    from app.routers import google as google_router

    def fake_auth_check():
        return True

    def fake_run(service: str, action: str, params: dict[str, object], *, confirm: bool = False):
        return GoogleWorkspaceResult(
            service=service,
            action=action,
            ok=True,
            summary="Found 2 unread messages",
            data=[{"id": "m1"}, {"id": "m2"}],
            raw_output='{"summary":"Found 2 unread messages"}',
        )

    monkeypatch.setattr(google_router, "auth_check", fake_auth_check)
    monkeypatch.setattr(google_router, "run", fake_run)

    res = client.post(
        "/api/v1/integrations/google/gmail/search",
        json={"params": {"query": "is:unread", "max": 2}},
        headers={"Authorization": f"Bearer {admin_tok}"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["service"] == "gmail"
    assert body["action"] == "search"
    assert body["summary"] == "Found 2 unread messages"
    assert body["data"] == [{"id": "m1"}, {"id": "m2"}]


def test_brain_google_requires_confirmation_for_destructive_action(client, admin_user):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": admin_user["email"], "password": admin_user["password"]},
    )
    tok = login.json()["access_token"]
    tfa = client.post(
        "/api/v1/auth/2fa/verify",
        json={"access_token": tok, "code": admin_user["code"]},
    )
    admin_tok = tfa.json()["access_token"]

    res = client.post(
        "/api/v1/brain/google",
        json={"text": "apagar arquivo do drive"},
        headers={"Authorization": f"Bearer {admin_tok}"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["requires_confirmation"] is True
    assert body["status"] == "needs_confirmation"
    assert body["service"] == "drive"
    assert body["action"] == "delete"


def test_brain_google_executes_search_with_summary(client, admin_user, monkeypatch):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": admin_user["email"], "password": admin_user["password"]},
    )
    tok = login.json()["access_token"]
    tfa = client.post(
        "/api/v1/auth/2fa/verify",
        json={"access_token": tok, "code": admin_user["code"]},
    )
    admin_tok = tfa.json()["access_token"]

    from app.routers import brain as brain_router

    def fake_run(service: str, action: str, params: dict[str, object], *, confirm: bool = False):
        return GoogleWorkspaceResult(
            service=service,
            action=action,
            ok=True,
            summary="Found 3 unread messages",
            data=[{"id": "m1"}, {"id": "m2"}, {"id": "m3"}],
            raw_output='{"summary":"Found 3 unread messages"}',
        )

    monkeypatch.setattr(brain_router, "run_google_workspace", fake_run)

    res = client.post(
        "/api/v1/brain/google",
        json={"text": "buscar e-mails não lidos"},
        headers={"Authorization": f"Bearer {admin_tok}"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["service"] == "gmail"
    assert body["action"] == "search"
    assert body["status"] == "done"
    assert body["summary"] == "Found 3 unread messages"
    assert body["data"] == [{"id": "m1"}, {"id": "m2"}, {"id": "m3"}]


def test_brain_google_reuses_existing_thread(client, admin_user, monkeypatch):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": admin_user["email"], "password": admin_user["password"]},
    )
    tok = login.json()["access_token"]
    tfa = client.post(
        "/api/v1/auth/2fa/verify",
        json={"access_token": tok, "code": admin_user["code"]},
    )
    admin_tok = tfa.json()["access_token"]

    from app.routers import brain as brain_router

    def fake_run(service: str, action: str, params: dict[str, object], *, confirm: bool = False):
        return GoogleWorkspaceResult(
            service=service,
            action=action,
            ok=True,
            summary="Listed calendar entries",
            data=[{"id": "e1"}],
            raw_output='{"summary":"Listed calendar entries"}',
        )

    monkeypatch.setattr(brain_router, "run_google_workspace", fake_run)

    first = client.post(
        "/api/v1/brain/google",
        json={"text": "listar agenda"},
        headers={"Authorization": f"Bearer {admin_tok}"},
    )
    assert first.status_code == 200
    first_body = first.json()
    assert first_body["thread_id"] is not None

    second = client.post(
        "/api/v1/brain/google",
        json={"text": "listar agenda", "thread_id": first_body["thread_id"]},
        headers={"Authorization": f"Bearer {admin_tok}"},
    )
    assert second.status_code == 200
    second_body = second.json()
    assert second_body["thread_id"] == first_body["thread_id"]


def test_google_natural_routes_email_send():
    routed = route_google_natural("Ei Jarvis, envie um e-mail para Maria com assunto Boas notícias e mensagem está tudo certo")
    assert routed.service == "gmail"
    assert routed.action == "send"
    assert routed.params["to"].lower().startswith("maria")
    assert routed.params["subject"] == "Boas notícias"
    assert "está tudo certo" in routed.params["body"]


def test_google_natural_routes_calendar_create():
    routed = route_google_natural("Jarvis, marque reunião amanhã às 10 com João")
    assert routed.service == "calendar"
    assert routed.action == "create"
    assert routed.params["calendar"] == "primary"
    assert routed.params["summary"]
    assert routed.params["start"] < routed.params["end"]


def test_brain_utterance_routes_google_and_returns_summary(client, admin_user, monkeypatch):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": admin_user["email"], "password": admin_user["password"]},
    )
    tok = login.json()["access_token"]
    tfa = client.post(
        "/api/v1/auth/2fa/verify",
        json={"access_token": tok, "code": admin_user["code"]},
    )
    admin_tok = tfa.json()["access_token"]

    from app.routers import brain as brain_router

    def fake_run(service: str, action: str, params: dict[str, object], *, confirm: bool = False):
        return GoogleWorkspaceResult(
            service=service,
            action=action,
            ok=True,
            summary="E-mail enviado",
            data={"message_id": "m1"},
            raw_output='{"summary":"E-mail enviado"}',
        )

    monkeypatch.setattr(brain_router, "run_google_workspace", fake_run)

    res = client.post(
        "/api/v1/brain/utterance",
        json={"text": "Ei Jarvis, envie um e-mail para Maria com assunto Boas notícias e mensagem está tudo certo"},
        headers={"Authorization": f"Bearer {admin_tok}"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["kind"] == "google"
    assert body["status"] == "done"
    assert body["summary"] == "E-mail enviado"
