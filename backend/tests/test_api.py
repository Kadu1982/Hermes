import pytest
from fastapi.testclient import TestClient

from app.command_wait import format_command_result_message


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
        json={"text": "Ei Jarvis, me leva para casa"},
        headers=headers,
    )
    assert nav.status_code == 201
    body = nav.json()
    assert body["parsed_type"] == "navigate_to"
    assert body["parsed_device_name"] == "HermesPhone"
    assert body["command"]["payload"]["destination"].lower() == "casa"
    assert body["command"]["payload"]["mode"] == "driving"


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
        result={"destination": "casa", "opened_url": "google.navigation:q=casa"},
    )
    assert "Navegação aberta" in nav
    assert "google.navigation:q=casa" in nav
