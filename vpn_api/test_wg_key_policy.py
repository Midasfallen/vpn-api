
from fastapi.testclient import TestClient

from vpn_api.main import app

client = TestClient(app)


def _register_and_auth(email: str, password: str = "strongpass"):
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code == 200
    user = r.json()
    r = client.post(
        "/auth/admin/promote", params={"user_id": user["id"], "secret": "bootstrap-secret"}
    )
    assert r.status_code in (200, 201, 204, 403)
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200
    token = r.json()["access_token"]
    return user, {"Authorization": f"Bearer {token}"}


def test_create_peer_with_host_key(monkeypatch):
    # simulate host key generation
    def fake_gen(base_name, outdir="/etc/wg-keys"):
        return {"private": f"/etc/wg-keys/{base_name}.key", "public": "pub-from-host"}

    # patch the function where peers.create_peer imports it
    monkeypatch.setattr("vpn_api.peers.generate_key_on_host", fake_gen)
    monkeypatch.setenv("WG_KEY_POLICY", "host")
    # enable host operations for test
    monkeypatch.setenv("WG_APPLY_ENABLED", "1")

    user, headers = _register_and_auth("hostkey@example.com")

    payload = {
        "user_id": user["id"],
        "wg_public_key": "ignored",
        "wg_ip": "10.0.0.7/32",
        "allowed_ips": "0.0.0.0/0",
    }

    resp = client.post("/vpn_peers/", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["wg_public_key"] == "pub-from-host"
    # private is not exposed by API response schema; ensure public key came from host
    assert data["wg_public_key"] == "pub-from-host"
