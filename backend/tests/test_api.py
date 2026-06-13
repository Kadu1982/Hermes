import pytest
from fastapi.testclient import TestClient
from uuid import UUID

from app.command_wait import format_command_result_message
from app.models import FileRecord


def test_health(client: TestClient):
    r = client.get("/healthz")
    assert r.status_code == 200


def test_pair_and_command_flow(client: TestClient, admin_user):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": admin_user["email"], "password": admin_user["password"]},
    )
    assert login.status_code == 200
    tok = login.json()["access_token"]
    tfa = client.post(
        "/api/v1/auth/2fa/verify",
        json={"access_token": tok, "code": admin_user["code"]},
    )
    assert tfa.status_code == 200
    admin_tok = tfa.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_tok}"}

    pc = client.post("/api/v1/pairing/codes", json={"label": "t"}, headers=headers)
    assert pc.status_code == 201
    code = pc.json()["code"]

    pair = client.post(
        "/api/v1/devices/pair",
        json={"pairing_code": code, "device_name": "Pixel"},
    )
    assert pair.status_code == 201
    dev_tok = pair.json()["device_token"]
    dheaders = {"Authorization": f"Bearer {dev_tok}"}

    hb = client.post(
        "/api/v1/devices/me/heartbeat",
        json={"battery_percent": 80, "network_type": "wifi", "app_version": "1.2-mvp", "inventory": {"foo": "bar"}},
        headers=dheaders,
    )
    assert hb.status_code == 204

    me = client.get("/api/v1/devices/me", headers=dheaders)
    assert me.status_code == 200
    assert me.json()["inventory"]["foo"] == "bar"

    dev_id = pair.json()["device_id"]
    detail = client.get(f"/api/v1/devices/{dev_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["token_version"] == 1
    assert detail.json()["inventory"]["foo"] == "bar"

    cmd = client.post(
        f"/api/v1/devices/{dev_id}/commands",
        json={
            "type": "ping",
            "payload": None,
            "notify_channel": "voice",
            "notify_on": "done",
            "source_text": "ping the device",
        },
        headers=headers,
    )
    assert cmd.status_code == 201
    assert cmd.json()["notify_channel"] == "voice"
    assert cmd.json()["source_text"] == "ping the device"
    cid = cmd.json()["id"]

    history = client.get(f"/api/v1/devices/{dev_id}/commands?limit=10&offset=0", headers=headers)
    assert history.status_code == 200
    assert history.json()["items"][0]["notify_channel"] == "voice"
    assert history.json()["items"][0]["source_text"] == "ping the device"

    nxt = client.get("/api/v1/devices/me/commands/next", headers=dheaders)
    assert nxt.status_code == 200
    assert nxt.json()["id"] == cid

    done = client.post(
        f"/api/v1/devices/me/commands/{cid}/complete",
        json={"status": "done", "result": {"pong": True}},
        headers=dheaders,
    )
    assert done.status_code == 204

    rot = client.post("/api/v1/devices/me/rotate-token", headers=dheaders)
    assert rot.status_code == 200
    new_tok = rot.json()["device_token"]
    assert client.get("/api/v1/devices/me", headers={"Authorization": f"Bearer {new_tok}"}).status_code == 200
    assert client.get("/api/v1/devices/me", headers=dheaders).status_code == 401

    rv = client.post(f"/api/v1/devices/{dev_id}/revoke", headers=headers)
    assert rv.status_code == 204
    assert (
        client.get("/api/v1/devices/me", headers={"Authorization": f"Bearer {new_tok}"}).status_code
        == 401
    )


def test_device_creates_command_for_another_device(client: TestClient, admin_user):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": admin_user["email"], "password": admin_user["password"]},
    )
    assert login.status_code == 200
    tok = login.json()["access_token"]
    tfa = client.post(
        "/api/v1/auth/2fa/verify",
        json={"access_token": tok, "code": admin_user["code"]},
    )
    assert tfa.status_code == 200
    admin_tok = tfa.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_tok}"}

    pc_a = client.post("/api/v1/pairing/codes", json={"label": "dA"}, headers=headers)
    assert pc_a.status_code == 201
    pc_b = client.post("/api/v1/pairing/codes", json={"label": "dB"}, headers=headers)
    assert pc_b.status_code == 201

    pair_a = client.post(
        "/api/v1/devices/pair",
        json={"pairing_code": pc_a.json()["code"], "device_name": "DeviceA"},
    )
    assert pair_a.status_code == 201
    pair_b = client.post(
        "/api/v1/devices/pair",
        json={"pairing_code": pc_b.json()["code"], "device_name": "DeviceB"},
    )
    assert pair_b.status_code == 201

    tok_a = pair_a.json()["device_token"]
    bid = pair_b.json()["device_id"]
    headers_a = {"Authorization": f"Bearer {tok_a}"}

    cmd = client.post(
        f"/api/v1/devices/{bid}/commands",
        json={"type": "ping"},
        headers=headers_a,
    )
    assert cmd.status_code == 201
    assert cmd.json()["status"] == "pending"
    assert cmd.json()["created_by_device_id"] == pair_a.json()["device_id"]
    cid = cmd.json()["id"]

    tok_b = pair_b.json()["device_token"]
    headers_b = {"Authorization": f"Bearer {tok_b}"}
    nxt = client.get("/api/v1/devices/me/commands/next", headers=headers_b)
    assert nxt.status_code == 200
    assert nxt.json()["id"] == cid

    done = client.post(
        f"/api/v1/devices/me/commands/{cid}/complete",
        json={"status": "done", "result": {"ok": True}},
        headers=headers_b,
    )
    assert done.status_code == 204


def test_natural_command_reuses_recent_context(client: TestClient, admin_user):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": admin_user["email"], "password": admin_user["password"]},
    )
    assert login.status_code == 200
    tok = login.json()["access_token"]
    tfa = client.post(
        "/api/v1/auth/2fa/verify",
        json={"access_token": tok, "code": admin_user["code"]},
    )
    assert tfa.status_code == 200
    admin_tok = tfa.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_tok}"}

    pc = client.post("/api/v1/pairing/codes", json={"label": "ctx"}, headers=headers)
    assert pc.status_code == 201
    pair_a = client.post(
        "/api/v1/devices/pair",
        json={"pairing_code": pc.json()["code"], "device_name": "DeviceA"},
    )
    assert pair_a.status_code == 201

    pc2 = client.post("/api/v1/pairing/codes", json={"label": "ctx2"}, headers=headers)
    assert pc2.status_code == 201
    pair_b = client.post(
        "/api/v1/devices/pair",
        json={"pairing_code": pc2.json()["code"], "device_name": "DeviceB"},
    )
    assert pair_b.status_code == 201

    first = client.post(
        "/api/v1/commands/natural",
        json={"text": "ping no DeviceA", "notify_channel": "silent", "notify_on": "done"},
        headers=headers,
    )
    assert first.status_code == 201
    first_data = first.json()
    assert first_data["parsed_device_name"] == "DeviceA"
    thread_id = first_data["thread_id"]
    assert thread_id is not None

    second = client.post(
        "/api/v1/commands/natural",
        json={"text": "continua", "notify_channel": "silent", "notify_on": "done"},
        headers=headers,
    )
    assert second.status_code == 201
    second_data = second.json()
    assert second_data["parsed_device_name"] == "DeviceA"
    assert second_data["parsed_type"] == "ping"
    assert second_data["thread_id"] == thread_id

    brain_ctx = client.get(
        f"/api/v1/brain/context?actor_type=user&actor_id={admin_user['user'].id}",
        headers={"X-Hermes-Brain-Key": "test-brain-key"},
    )
    assert brain_ctx.status_code == 200
    body = brain_ctx.json()
    assert body["thread"]["id"] == thread_id
    assert body["thread"]["last_intent"] == "ping"
    assert body["thread"]["last_target_device_id"] == pair_a.json()["device_id"]
    assert body["recent_threads"][0]["id"] == thread_id


def test_natural_command_routes_photo_and_location(client: TestClient, admin_user):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": admin_user["email"], "password": admin_user["password"]},
    )
    assert login.status_code == 200
    tok = login.json()["access_token"]
    tfa = client.post(
        "/api/v1/auth/2fa/verify",
        json={"access_token": tok, "code": admin_user["code"]},
    )
    assert tfa.status_code == 200
    admin_tok = tfa.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_tok}"}

    pc = client.post("/api/v1/pairing/codes", json={"label": "phone"}, headers=headers)
    assert pc.status_code == 201
    pair = client.post(
        "/api/v1/devices/pair",
        json={"pairing_code": pc.json()["code"], "device_name": "HermesPhone"},
    )
    assert pair.status_code == 201
    dev_id = pair.json()["device_id"]

    photo = client.post(
        "/api/v1/commands/natural",
        json={"text": "Ei Jarvis, tira uma foto no telefone", "device_id": dev_id},
        headers=headers,
    )
    assert photo.status_code == 201
    assert photo.json()["parsed_type"] == "take_photo"
    assert photo.json()["command"]["payload"]["archive_only"] is True

    location = client.post(
        "/api/v1/commands/natural",
        json={"text": "Ei Jarvis, onde estou no telefone", "device_id": dev_id},
        headers=headers,
    )
    assert location.status_code == 201
    assert location.json()["parsed_type"] == "get_location"


def test_file_search_lists_device_files(client: TestClient, admin_user, db_session):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": admin_user["email"], "password": admin_user["password"]},
    )
    assert login.status_code == 200
    tok = login.json()["access_token"]
    tfa = client.post(
        "/api/v1/auth/2fa/verify",
        json={"access_token": tok, "code": admin_user["code"]},
    )
    assert tfa.status_code == 200
    admin_tok = tfa.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_tok}"}

    pc = client.post("/api/v1/pairing/codes", json={"label": "files"}, headers=headers)
    assert pc.status_code == 201
    pair = client.post(
        "/api/v1/devices/pair",
        json={"pairing_code": pc.json()["code"], "device_name": "FileDevice"},
    )
    assert pair.status_code == 201
    dev_id = UUID(pair.json()["device_id"])

    cmd = client.post(f"/api/v1/devices/{dev_id}/commands", json={"type": "ping"}, headers=headers)
    assert cmd.status_code == 201
    cid = UUID(cmd.json()["id"])

    rec = FileRecord(
        device_id=dev_id,
        command_id=cid,
        filename="relatorio-final.pdf",
        storage_path=f"{cid}_relatorio-final.pdf",
        size_bytes=1234,
        sha256="a" * 64,
    )
    db_session.add(rec)
    db_session.commit()

    r = client.get("/api/v1/files?query=relatorio", headers={"Authorization": f"Bearer {pair.json()['device_token']}"})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["filename"] == "relatorio-final.pdf"


def test_natural_command_routes_navigation_to_phone(client: TestClient, admin_user):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": admin_user["email"], "password": admin_user["password"]},
    )
    assert login.status_code == 200
    tok = login.json()["access_token"]
    tfa = client.post(
        "/api/v1/auth/2fa/verify",
        json={"access_token": tok, "code": admin_user["code"]},
    )
    assert tfa.status_code == 200
    admin_tok = tfa.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_tok}"}

    pc = client.post("/api/v1/pairing/codes", json={"label": "phone"}, headers=headers)
    assert pc.status_code == 201
    phone = client.post(
        "/api/v1/devices/pair",
        json={"pairing_code": pc.json()["code"], "device_name": "HermesPhone"},
    )
    assert phone.status_code == 201

    pc2 = client.post("/api/v1/pairing/codes", json={"label": "pc"}, headers=headers)
    assert pc2.status_code == 201
    desktop = client.post(
        "/api/v1/devices/pair",
        json={"pairing_code": pc2.json()["code"], "device_name": "PC-Casa", "platform": "windows"},
    )
    assert desktop.status_code == 201

    nav = client.post(
        "/api/v1/commands/natural",
        json={"text": "Ei Jarvis, me leva para Rua Oscar Freire, 123, São Paulo - SP"},
        headers=headers,
    )
    assert nav.status_code == 201
    body = nav.json()
    assert body["parsed_type"] == "navigate_to"
    assert body["parsed_device_name"] == "HermesPhone"
    assert body["command"]["payload"]["destination"] == "Rua Oscar Freire, 123, São Paulo - SP"
    assert body["command"]["payload"]["mode"] == "driving"


def test_natural_command_routes_android_actions(client: TestClient, admin_user):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": admin_user["email"], "password": admin_user["password"]},
    )
    assert login.status_code == 200
    tok = login.json()["access_token"]
    tfa = client.post(
        "/api/v1/auth/2fa/verify",
        json={"access_token": tok, "code": admin_user["code"]},
    )
    assert tfa.status_code == 200
    admin_tok = tfa.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_tok}"}

    pc = client.post("/api/v1/pairing/codes", json={"label": "phone"}, headers=headers)
    assert pc.status_code == 201
    pair = client.post(
        "/api/v1/devices/pair",
        json={"pairing_code": pc.json()["code"], "device_name": "HermesPhone"},
    )
    assert pair.status_code == 201
    device_id = pair.json()["device_id"]

    open_app = client.post(
        "/api/v1/commands/natural",
        json={"text": "abre WhatsApp no meu telefone", "device_id": device_id},
        headers=headers,
    )
    assert open_app.status_code == 201
    assert open_app.json()["parsed_type"] == "open_app"
    assert open_app.json()["command"]["payload"]["app_name"] == "WhatsApp"
    assert open_app.json()["command"]["payload"]["package_name"] == "com.whatsapp"

    youtube = client.post(
        "/api/v1/commands/natural",
        json={"text": "abre YouTube no S25 Ultra"},
        headers=headers,
    )
    assert youtube.status_code == 201
    assert youtube.json()["parsed_type"] == "open_app"
    assert youtube.json()["command"]["payload"]["app_name"] == "YouTube"
    assert youtube.json()["command"]["payload"]["package_name"] == "com.google.android.youtube"

    home = client.post(
        "/api/v1/commands/natural",
        json={"text": "volta para home no S25"},
        headers=headers,
    )
    assert home.status_code == 201
    assert home.json()["parsed_type"] == "android_system_action"
    assert home.json()["command"]["payload"]["action"] == "home"

    quick_settings = client.post(
        "/api/v1/commands/natural",
        json={"text": "abre definições rápidas no celular"},
        headers=headers,
    )
    assert quick_settings.status_code == 201
    assert quick_settings.json()["parsed_type"] == "android_system_action"
    assert quick_settings.json()["command"]["payload"]["action"] == "quick_settings"

    camera = client.post(
        "/api/v1/commands/natural",
        json={"text": "abre a câmera no telefone"},
        headers=headers,
    )
    assert camera.status_code == 201
    assert camera.json()["parsed_type"] == "android_deep_link"
    assert camera.json()["command"]["payload"]["target"] == "camera"

    unlock = client.post(
        "/api/v1/commands/natural",
        json={"text": "desbloqueia o telefone"},
        headers=headers,
    )
    assert unlock.status_code == 201
    assert unlock.json()["parsed_type"] == "request_unlock"
    assert unlock.json()["command"]["payload"] is None


def test_android_command_payload_validation(client: TestClient, admin_user):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": admin_user["email"], "password": admin_user["password"]},
    )
    assert login.status_code == 200
    tok = login.json()["access_token"]
    tfa = client.post(
        "/api/v1/auth/2fa/verify",
        json={"access_token": tok, "code": admin_user["code"]},
    )
    assert tfa.status_code == 200
    admin_tok = tfa.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_tok}"}

    pc = client.post("/api/v1/pairing/codes", json={"label": "phone"}, headers=headers)
    assert pc.status_code == 201
    pair = client.post(
        "/api/v1/devices/pair",
        json={"pairing_code": pc.json()["code"], "device_name": "HermesPhone"},
    )
    assert pair.status_code == 201
    device_id = pair.json()["device_id"]

    invalid_open = client.post(
        f"/api/v1/devices/{device_id}/commands",
        json={"type": "open_app", "payload": {"package_name": "com.whatsapp"}},
        headers=headers,
    )
    assert invalid_open.status_code == 400
    assert "app_name" in invalid_open.json()["detail"]

    invalid_action = client.post(
        f"/api/v1/devices/{device_id}/commands",
        json={"type": "android_system_action", "payload": {"action": "sleep"}},
        headers=headers,
    )
    assert invalid_action.status_code == 400
    assert "invalid" in invalid_action.json()["detail"]

    invalid_deep_link = client.post(
        f"/api/v1/devices/{device_id}/commands",
        json={"type": "android_deep_link", "payload": {"target": "browser"}},
        headers=headers,
    )
    assert invalid_deep_link.status_code == 400
    assert "invalid" in invalid_deep_link.json()["detail"]

    invalid_unlock = client.post(
        f"/api/v1/devices/{device_id}/commands",
        json={"type": "request_unlock", "payload": {"reason": "test"}},
        headers=headers,
    )
    assert invalid_unlock.status_code == 400
    assert "does not accept payload" in invalid_unlock.json()["detail"]


def test_command_wait_formats_photo_and_location_messages():
    photo = format_command_result_message(
        device_name="HermesPhone",
        command_type="take_photo",
        status="done",
        result={"archived_path": "/data/user/0/com.hermes.app/files/hermes/photos/p.jpg", "share_requested": True},
    )
    assert "arquivada localmente" in photo
    assert "compartilhamento" in photo

    location = format_command_result_message(
        device_name="HermesPhone",
        command_type="get_location",
        status="done",
        result={"latitude": -23.5, "longitude": -46.6, "maps_url": "https://maps.example"},
    )
    assert "Localização de HermesPhone" in location
    assert "https://maps.example" in location

    nav = format_command_result_message(
        device_name="HermesPhone",
        command_type="navigate_to",
        status="done",
        result={
            "destination": "Rua Oscar Freire, 123, São Paulo - SP",
            "opened_url": "google.navigation:q=Rua%20Oscar%20Freire",
        },
    )
    assert "Navegação aberta" in nav
    assert "Rua Oscar Freire, 123, São Paulo - SP" in nav

    open_app = format_command_result_message(
        device_name="HermesPhone",
        command_type="open_app",
        status="done",
        result={"app_name": "WhatsApp", "opened": True},
    )
    assert "App aberto" in open_app


def test_natural_command_routes_screenshot(client: TestClient, admin_user):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": admin_user["email"], "password": admin_user["password"]},
    )
    assert login.status_code == 200
    tok = login.json()["access_token"]
    tfa = client.post(
        "/api/v1/auth/2fa/verify",
        json={"access_token": tok, "code": admin_user["code"]},
    )
    assert tfa.status_code == 200
    admin_tok = tfa.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_tok}"}

    pc_pc = client.post("/api/v1/pairing/codes", json={"label": "screenshot_pc"}, headers=headers)
    assert pc_pc.status_code == 201
    pc_casa = client.post(
        "/api/v1/devices/pair",
        json={"pairing_code": pc_pc.json()["code"], "device_name": "PC-Casa", "platform": "windows"},
    )
    assert pc_casa.status_code == 201

    for text, expected_type in [
        ("print da tela no PC-Casa", "take_screenshot"),
        ("Ei Jarvis, captura de tela no PC-Casa", "take_screenshot"),
        ("screenshot no PC", "take_screenshot"),
        ("captura de ecrã no PC-Casa", "take_screenshot"),
    ]:
        r = client.post("/api/v1/commands/natural", json={"text": text}, headers=headers)
        assert r.status_code == 201, f"failed for text={text!r}: {r.json()}"
        assert r.json()["parsed_type"] == expected_type, f"wrong type for text={text!r}"
        assert r.json()["parsed_device_name"] == "PC-Casa", f"wrong device for text={text!r}"
        assert r.json()["command"]["payload"] is None, f"expected null payload for text={text!r}"

    for text in ("tira uma foto no PC-Casa", "abre a câmera no PC-Casa"):
        r = client.post("/api/v1/commands/natural", json={"text": text}, headers=headers)
        assert r.status_code == 201, f"failed for text={text!r}"
        assert r.json()["parsed_type"] != "take_screenshot", f"text={text!r} should NOT be screenshot"


def test_screenshot_payload_validation(client: TestClient, admin_user):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": admin_user["email"], "password": admin_user["password"]},
    )
    assert login.status_code == 200
    tok = login.json()["access_token"]
    tfa = client.post(
        "/api/v1/auth/2fa/verify",
        json={"access_token": tok, "code": admin_user["code"]},
    )
    assert tfa.status_code == 200
    admin_tok = tfa.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_tok}"}

    pc = client.post("/api/v1/pairing/codes", json={"label": "val_pc"}, headers=headers)
    assert pc.status_code == 201
    pair = client.post(
        "/api/v1/devices/pair",
        json={"pairing_code": pc.json()["code"], "device_name": "TestPC", "platform": "windows"},
    )
    assert pair.status_code == 201
    device_id = pair.json()["device_id"]

    invalid = client.post(
        f"/api/v1/devices/{device_id}/commands",
        json={"type": "take_screenshot", "payload": {"format": "jpg"}},
        headers=headers,
    )
    assert invalid.status_code == 400
    assert "does not accept payload" in invalid.json()["detail"]

    valid = client.post(
        f"/api/v1/devices/{device_id}/commands",
        json={"type": "take_screenshot", "payload": None},
        headers=headers,
    )
    assert valid.status_code == 201
    assert valid.json()["type"] == "take_screenshot"
    assert valid.json()["payload"] is None


def test_read_local_file_payload_validation(client: TestClient, admin_user):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": admin_user["email"], "password": admin_user["password"]},
    )
    assert login.status_code == 200
    tok = login.json()["access_token"]
    tfa = client.post(
        "/api/v1/auth/2fa/verify",
        json={"access_token": tok, "code": admin_user["code"]},
    )
    assert tfa.status_code == 200
    admin_tok = tfa.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_tok}"}

    pc = client.post("/api/v1/pairing/codes", json={"label": "rl_pc"}, headers=headers)
    assert pc.status_code == 201
    pair = client.post(
        "/api/v1/devices/pair",
        json={"pairing_code": pc.json()["code"], "device_name": "PC-Casa", "platform": "windows"},
    )
    assert pair.status_code == 201
    device_id = pair.json()["device_id"]

    invalid_no_path = client.post(
        f"/api/v1/devices/{device_id}/commands",
        json={"type": "read_local_file", "payload": {}},
        headers=headers,
    )
    assert invalid_no_path.status_code == 400
    assert "filepath" in invalid_no_path.json()["detail"]

    invalid_extra = client.post(
        f"/api/v1/devices/{device_id}/commands",
        json={"type": "read_local_file", "payload": {"filepath": "C:\\test.txt", "extra": "bad"}},
        headers=headers,
    )
    assert invalid_extra.status_code == 400
    assert "only accepts" in invalid_extra.json()["detail"]

    valid = client.post(
        f"/api/v1/devices/{device_id}/commands",
        json={"type": "read_local_file", "payload": {"filepath": "C:\\Users\\me\\doc.txt"}},
        headers=headers,
    )
    assert valid.status_code == 201
    assert valid.json()["type"] == "read_local_file"
    assert valid.json()["payload"]["filepath"] == "C:\\Users\\me\\doc.txt"


def test_natural_command_routes_read_local_file(client: TestClient, admin_user):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": admin_user["email"], "password": admin_user["password"]},
    )
    assert login.status_code == 200
    tok = login.json()["access_token"]
    tfa = client.post(
        "/api/v1/auth/2fa/verify",
        json={"access_token": tok, "code": admin_user["code"]},
    )
    assert tfa.status_code == 200
    admin_tok = tfa.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_tok}"}

    pc = client.post("/api/v1/pairing/codes", json={"label": "rl_pc2"}, headers=headers)
    assert pc.status_code == 201
    pair = client.post(
        "/api/v1/devices/pair",
        json={"pairing_code": pc.json()["code"], "device_name": "PC-Casa", "platform": "windows"},
    )
    assert pair.status_code == 201
    device_id = pair.json()["device_id"]

    for text, expected_path in [
        ("leia o arquivo C:\\Users\\meu\\documento.txt no PC-Casa", "C:\\Users\\meu\\documento.txt"),
        ("ler arquivo /home/user/file.txt no PC", "/home/user/file.txt"),
        ("mostra o arquivo /etc/config.conf no PC-Casa", "/etc/config.conf"),
    ]:
        r = client.post(
            "/api/v1/commands/natural",
            json={"text": text, "device_id": device_id},
            headers=headers,
        )
        assert r.status_code == 201, f"failed for text={text!r}: {r.json()}"
        assert r.json()["parsed_type"] == "read_local_file", f"wrong type for text={text!r}"
        assert r.json()["command"]["payload"]["filepath"] == expected_path, f"wrong path for text={text!r}"


def test_command_wait_formats_read_local_file():
    inline_read = format_command_result_message(
        device_name="PC-Casa",
        command_type="read_local_file",
        status="done",
        result={"filename": "notes.txt", "content": "Hello world line 1\nline 2\n", "size_bytes": 28, "content_type": "text"},
    )
    assert "Arquivo lido em PC-Casa" in inline_read
    assert "notes.txt" in inline_read
    assert "Hello world line 1" in inline_read

    file_id_result = format_command_result_message(
        device_name="PC-Casa",
        command_type="read_local_file",
        status="done",
        result={"file_id": "abc-456", "filename": "photo.jpg", "size_bytes": 1024000},
    )
    assert "Arquivo lido em PC-Casa" in file_id_result
    assert "photo.jpg" in file_id_result
    assert "abc-456" in file_id_result

    failed = format_command_result_message(
        device_name="PC-Casa",
        command_type="read_local_file",
        status="failed",
        result={"error": "File not found"},
    )
    assert "FALHOU" in failed


def test_restart_agent_command_flow(client: TestClient, admin_user):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": admin_user["email"], "password": admin_user["password"]},
    )
    assert login.status_code == 200
    tok = login.json()["access_token"]
    tfa = client.post(
        "/api/v1/auth/2fa/verify",
        json={"access_token": tok, "code": admin_user["code"]},
    )
    assert tfa.status_code == 200
    admin_tok = tfa.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_tok}"}

    pc = client.post("/api/v1/pairing/codes", json={"label": "restart_pc"}, headers=headers)
    assert pc.status_code == 201
    pair = client.post(
        "/api/v1/devices/pair",
        json={"pairing_code": pc.json()["code"], "device_name": "PC-Casa", "platform": "windows"},
    )
    assert pair.status_code == 201
    dev_id = pair.json()["device_id"]
    dheaders = {"Authorization": f"Bearer {pair.json()['device_token']}"}

    cmd = client.post(
        f"/api/v1/devices/{dev_id}/commands",
        json={"type": "restart_agent", "payload": None},
        headers=headers,
    )
    assert cmd.status_code == 201
    assert cmd.json()["type"] == "restart_agent"
    assert cmd.json()["payload"] is None
    cid = cmd.json()["id"]

    nxt = client.get("/api/v1/devices/me/commands/next", headers=dheaders)
    assert nxt.status_code == 200
    assert nxt.json()["type"] == "restart_agent"

    done = client.post(
        f"/api/v1/devices/me/commands/{cid}/complete",
        json={"status": "done", "result": {"restarting": True}},
        headers=dheaders,
    )
    assert done.status_code == 204


def test_restart_agent_payload_validation(client: TestClient, admin_user):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": admin_user["email"], "password": admin_user["password"]},
    )
    assert login.status_code == 200
    tok = login.json()["access_token"]
    tfa = client.post(
        "/api/v1/auth/2fa/verify",
        json={"access_token": tok, "code": admin_user["code"]},
    )
    assert tfa.status_code == 200
    admin_tok = tfa.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_tok}"}

    pc = client.post("/api/v1/pairing/codes", json={"label": "restart_val"}, headers=headers)
    assert pc.status_code == 201
    pair = client.post(
        "/api/v1/devices/pair",
        json={"pairing_code": pc.json()["code"], "device_name": "TestPC", "platform": "windows"},
    )
    assert pair.status_code == 201
    dev_id = pair.json()["device_id"]

    invalid = client.post(
        f"/api/v1/devices/{dev_id}/commands",
        json={"type": "restart_agent", "payload": {"reason": "manutencao"}},
        headers=headers,
    )
    assert invalid.status_code == 400
    assert "Payload must be empty" in invalid.json()["detail"]

    valid = client.post(
        f"/api/v1/devices/{dev_id}/commands",
        json={"type": "restart_agent", "payload": None},
        headers=headers,
    )
    assert valid.status_code == 201
    assert valid.json()["type"] == "restart_agent"


def test_restart_pc_command_flow(client: TestClient, admin_user):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": admin_user["email"], "password": admin_user["password"]},
    )
    assert login.status_code == 200
    tok = login.json()["access_token"]
    tfa = client.post(
        "/api/v1/auth/2fa/verify",
        json={"access_token": tok, "code": admin_user["code"]},
    )
    assert tfa.status_code == 200
    admin_tok = tfa.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_tok}"}

    pc = client.post("/api/v1/pairing/codes", json={"label": "reboot_pc"}, headers=headers)
    assert pc.status_code == 201
    pair = client.post(
        "/api/v1/devices/pair",
        json={"pairing_code": pc.json()["code"], "device_name": "PC-Casa", "platform": "windows"},
    )
    assert pair.status_code == 201
    dev_id = pair.json()["device_id"]
    dheaders = {"Authorization": f"Bearer {pair.json()['device_token']}"}

    cmd = client.post(
        f"/api/v1/devices/{dev_id}/commands",
        json={"type": "restart_pc", "payload": None},
        headers=headers,
    )
    assert cmd.status_code == 201
    assert cmd.json()["type"] == "restart_pc"
    assert cmd.json()["payload"] is None
    cid = cmd.json()["id"]

    nxt = client.get("/api/v1/devices/me/commands/next", headers=dheaders)
    assert nxt.status_code == 200
    assert nxt.json()["type"] == "restart_pc"

    done = client.post(
        f"/api/v1/devices/me/commands/{cid}/complete",
        json={"status": "done", "result": {"rebooting": True}},
        headers=dheaders,
    )
    assert done.status_code == 204


def test_restart_pc_payload_validation(client: TestClient, admin_user):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": admin_user["email"], "password": admin_user["password"]},
    )
    assert login.status_code == 200
    tok = login.json()["access_token"]
    tfa = client.post(
        "/api/v1/auth/2fa/verify",
        json={"access_token": tok, "code": admin_user["code"]},
    )
    assert tfa.status_code == 200
    admin_tok = tfa.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_tok}"}

    pc = client.post("/api/v1/pairing/codes", json={"label": "reboot_val"}, headers=headers)
    assert pc.status_code == 201
    pair = client.post(
        "/api/v1/devices/pair",
        json={"pairing_code": pc.json()["code"], "device_name": "TestPC", "platform": "windows"},
    )
    assert pair.status_code == 201
    dev_id = pair.json()["device_id"]

    invalid = client.post(
        f"/api/v1/devices/{dev_id}/commands",
        json={"type": "restart_pc", "payload": {"reason": "manutencao"}},
        headers=headers,
    )
    assert invalid.status_code == 400
    assert "Payload must be empty" in invalid.json()["detail"]

    valid = client.post(
        f"/api/v1/devices/{dev_id}/commands",
        json={"type": "restart_pc", "payload": None},
        headers=headers,
    )
    assert valid.status_code == 201
    assert valid.json()["type"] == "restart_pc"


def test_natural_command_routes_restart_pc(client: TestClient, admin_user):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": admin_user["email"], "password": admin_user["password"]},
    )
    assert login.status_code == 200
    tok = login.json()["access_token"]
    tfa = client.post(
        "/api/v1/auth/2fa/verify",
        json={"access_token": tok, "code": admin_user["code"]},
    )
    assert tfa.status_code == 200
    admin_tok = tfa.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_tok}"}

    pc = client.post("/api/v1/pairing/codes", json={"label": "reboot_nl"}, headers=headers)
    assert pc.status_code == 201
    pair = client.post(
        "/api/v1/devices/pair",
        json={"pairing_code": pc.json()["code"], "device_name": "PC-Casa", "platform": "windows"},
    )
    assert pair.status_code == 201

    for text, expected_type in [
        ("reiniciar o PC no PC-Casa", "restart_pc"),
        ("Ei Jarvis, reinicie o PC-Casa", "restart_pc"),
        ("restart PC no PC-Casa", "restart_pc"),
        ("reiniciar o computador no PC-Casa", "restart_pc"),
        ("reiniciar a máquina no PC-Casa", "restart_pc"),
    ]:
        r = client.post("/api/v1/commands/natural", json={"text": text}, headers=headers)
        assert r.status_code == 201, f"failed for text={text!r}: {r.json()}"
        assert r.json()["parsed_type"] == expected_type, f"wrong type for text={text!r}"
        assert r.json()["parsed_device_name"] == "PC-Casa", f"wrong device for text={text!r}"
        assert r.json()["command"]["payload"] is None, f"expected null payload for text={text!r}"


def test_command_wait_formats_restart_pc():
    msg = format_command_result_message(
        device_name="PC-Casa",
        command_type="restart_pc",
        status="done",
        result={"rebooting": True},
    )
    assert "PC reiniciado em PC-Casa" in msg


def test_natural_command_routes_restart_agent(client: TestClient, admin_user):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": admin_user["email"], "password": admin_user["password"]},
    )
    assert login.status_code == 200
    tok = login.json()["access_token"]
    tfa = client.post(
        "/api/v1/auth/2fa/verify",
        json={"access_token": tok, "code": admin_user["code"]},
    )
    assert tfa.status_code == 200
    admin_tok = tfa.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_tok}"}

    pc = client.post("/api/v1/pairing/codes", json={"label": "restart_nl"}, headers=headers)
    assert pc.status_code == 201
    pair = client.post(
        "/api/v1/devices/pair",
        json={"pairing_code": pc.json()["code"], "device_name": "PC-Casa", "platform": "windows"},
    )
    assert pair.status_code == 201

    for text, expected_type in [
        ("reiniciar agente no PC-Casa", "restart_agent"),
        ("Ei Jarvis, reinicie o agente no PC-Casa", "restart_agent"),
        ("restart agent no PC", "restart_agent"),
    ]:
        r = client.post("/api/v1/commands/natural", json={"text": text}, headers=headers)
        assert r.status_code == 201, f"failed for text={text!r}: {r.json()}"
        assert r.json()["parsed_type"] == expected_type, f"wrong type for text={text!r}"
        assert r.json()["parsed_device_name"] == "PC-Casa", f"wrong device for text={text!r}"
        assert r.json()["command"]["payload"] is None, f"expected null payload for text={text!r}"


def test_command_wait_formats_restart_agent():
    msg = format_command_result_message(
        device_name="PC-Casa",
        command_type="restart_agent",
        status="done",
        result={"restarting": True},
    )
    assert "Agente reiniciado em PC-Casa" in msg


def test_command_wait_formats_screenshot_message():
    msg = format_command_result_message(
        device_name="PC-Casa",
        command_type="take_screenshot",
        status="done",
        result={"file_id": "abc-123", "filename": "screenshot_2026_05_27.png", "size_bytes": 245760, "sha256": "deadbeef"},
    )
    assert "Screenshot capturado em PC-Casa" in msg
    assert "screenshot_2026_05_27.png" in msg
    assert "245760" in msg

    no_file = format_command_result_message(
        device_name="PC-Casa",
        command_type="take_screenshot",
        status="done",
        result={"some_other": "data"},
    )
    assert "Screenshot capturado em PC-Casa" in no_file

    failed = format_command_result_message(
        device_name="PC-Casa",
        command_type="take_screenshot",
        status="failed",
        result={"error": "no screen available"},
    )
    assert "FALHOU" in failed
