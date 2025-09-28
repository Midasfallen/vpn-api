import os

from fastapi.testclient import TestClient

from vpn_api.main import app

client = TestClient(app)


def test_create_self_db_mode_minimal(monkeypatch):
    # Ensure db policy accepts minimal payload (no wg_public_key/wg_ip)
    os.environ["WG_KEY_POLICY"] = "db"

    # Create a test user and login via test helpers in auth tests is out-of-scope.
    # Instead, use a token by creating a test user via the auth endpoints.
    # For simplicity, assume conftest set SECRET_KEY and DB initialized.
    resp = client.post(
        "/auth/register", json={"email": "u1@example.com", "password": "testpass123"}
    )
    assert resp.status_code in (200, 201)
    # login
    login = client.post("/auth/login", json={"email": "u1@example.com", "password": "testpass123"})
    assert login.status_code == 200
    token = login.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}
    r = client.post("/vpn_peers/self", json={"device_name": "phone"}, headers=headers)
    assert r.status_code == 200
    data = r.json()
    # private key generated in db mode (random token) should be present in DB but may be obfuscated
    assert "wg_private_key" in data


def test_create_self_host_mode(monkeypatch):
    os.environ["WG_KEY_POLICY"] = "host"

    # Mock generate_key_on_host to return sample keys
    def fake_gen(base_name, outdir="/etc/wg-keys"):
        return {"private": "/etc/wg-keys/priv.key", "public": "PUB_HOST_ABC"}

    monkeypatch.setattr("vpn_api.peers.generate_key_on_host", fake_gen)

    # Prepare auth
    resp = client.post(
        "/auth/register", json={"email": "u2@example.com", "password": "testpass123"}
    )
    assert resp.status_code in (200, 201)
    login = client.post("/auth/login", json={"email": "u2@example.com", "password": "testpass123"})
    token = login.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}
    r = client.post("/vpn_peers/self", json={"device_name": "phone"}, headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data.get("wg_public_key") == "PUB_HOST_ABC"
    # private key marker should indicate host-generated
    assert data.get("wg_private_key") is not None


def test_create_self_wg_easy_parses_config(monkeypatch):
    os.environ["WG_KEY_POLICY"] = "wg-easy"
    os.environ.setdefault("WG_EASY_URL", "http://example.local")
    os.environ.setdefault("WG_EASY_PASSWORD", "pw")

    # Mock _create_wg_easy_client to return a created client
    def fake_create(url, pw, name):
        return {"publicKey": "PUB_WG_123", "id": "cid123"}

    # Mock _get_wg_easy_client_config to return wg-quick text
    sample_cfg = (
        b"[Interface]\nPrivateKey = PRIVATE_ABC\nAddress = 10.10.0.99/32\n"
        b"[Peer]\nAllowedIPs = 0.0.0.0/0\n"
        b"Endpoint = vpn.example.com:51820\n"
    )

    def fake_get_config(url, pw, client_id):
        return sample_cfg

    monkeypatch.setattr("vpn_api.peers._create_wg_easy_client", fake_create)
    monkeypatch.setattr("vpn_api.peers._get_wg_easy_client_config", fake_get_config)

    resp = client.post(
        "/auth/register", json={"email": "u3@example.com", "password": "testpass123"}
    )
    assert resp.status_code in (200, 201)
    login = client.post("/auth/login", json={"email": "u3@example.com", "password": "testpass123"})
    token = login.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}
    r = client.post("/vpn_peers/self", json={"device_name": "phone"}, headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("wg_public_key") == "PUB_WG_123"
    assert data.get("wg_private_key") == "PRIVATE_ABC"
    assert data.get("wg_ip") == "10.10.0.99/32"
    assert data.get("allowed_ips") == "0.0.0.0/0"
