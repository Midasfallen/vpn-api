import os

from fastapi.testclient import TestClient

from vpn_api.main import app


def _ensure_key():
    # Ensure an encryption key is available for the test env
    if not os.getenv("CONFIG_ENCRYPTION_KEY"):
        # generate a test Fernet key
        from cryptography.fernet import Fernet

        os.environ["CONFIG_ENCRYPTION_KEY"] = Fernet.generate_key().decode()


def test_create_peer_and_get_config(tmp_path):
    _ensure_key()
    client = TestClient(app)
    # register user
    r = client.post("/auth/register", json={"email": "cfgtest@example.com", "password": "passw0rd"})
    assert r.status_code == 200
    token = client.post(
        "/auth/login", json={"email": "cfgtest@example.com", "password": "passw0rd"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    # create peer for self
    r = client.post("/vpn_peers/self", json={"device_name": "phone"}, headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert "wg_private_key" in data
    # now fetch config
    r2 = client.get("/vpn_peers/self/config", headers=headers)
    assert r2.status_code == 200
    body = r2.json()
    assert "wg_quick" in body and body["wg_quick"].startswith("[Interface]")
