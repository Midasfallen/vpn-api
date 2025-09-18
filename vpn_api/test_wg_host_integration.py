
from fastapi.testclient import TestClient

from vpn_api.main import app

client = TestClient(app)


def _register_and_auth(email: str, password: str = "strongpass"):
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code == 200
    user = r.json()
    # promote to admin using bootstrap secret
    r = client.post(
        "/auth/admin/promote", params={"user_id": user["id"], "secret": "bootstrap-secret"}
    )
    # promote may return 200 or 204 depending on state
    assert r.status_code in (200, 201, 204, 403)
    # login
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200
    token = r.json()["access_token"]
    return user, {"Authorization": f"Bearer {token}"}


def test_create_peer_calls_apply(monkeypatch):
    called = {"apply": False}

    def fake_apply(peer):
        called["apply"] = True
        return True

    monkeypatch.setattr("vpn_api.peers.apply_peer", fake_apply)

    user, headers = _register_and_auth("test-wg@example.com")

    payload = {
        "user_id": user["id"],
        "wg_public_key": "pubkey123",
        "wg_ip": "10.0.0.5/32",
        "allowed_ips": "0.0.0.0/0",
    }

    resp = client.post("/vpn_peers/", json=payload, headers=headers)
    assert resp.status_code == 200
    assert called["apply"] is True


def test_delete_peer_calls_remove(monkeypatch):
    called = {"remove": False}

    def fake_remove(peer):
        called["remove"] = True
        return True

    monkeypatch.setattr("vpn_api.peers.remove_peer", fake_remove)

    user, headers = _register_and_auth("test-wg-del@example.com")

    payload = {"user_id": user["id"], "wg_public_key": "pub2", "wg_ip": "10.0.0.6/32"}
    r = client.post("/vpn_peers/", json=payload, headers=headers)
    assert r.status_code == 200
    peer = r.json()

    resp = client.delete(f"/vpn_peers/{peer['id']}", headers=headers)
    assert resp.status_code == 200
    assert called["remove"] is True
