from fastapi.testclient import TestClient

from vpn_api.main import app

client = TestClient(app)


def test_peers_crud_flow():
    # register a user
    r = client.post("/auth/register", json={"email": "peer@example.com", "password": "strongpass"})
    assert r.status_code == 200
    user = r.json()
    # bootstrap promote to admin
    r = client.post(
        "/auth/admin/promote", params={"user_id": user["id"], "secret": "bootstrap-secret"}
    )
    assert r.status_code in (200, 201, 204, 403)
    # login
    r = client.post("/auth/login", json={"email": "peer@example.com", "password": "strongpass"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # create tariff to attach (not necessary for peer but keep flow minimal)
    r = client.post(
        "/tariffs/",
        json={"name": "t1", "price": 10, "duration_days": 30, "description": "d"},
        headers=headers,
    )

    # create peer for user
    payload = {"user_id": user["id"], "wg_public_key": "pubkey1", "wg_ip": "10.0.0.2/32"}
    r = client.post("/vpn_peers/", json=payload, headers=headers)
    assert r.status_code == 200
    peer = r.json()
    assert peer["wg_public_key"] == "pubkey1"

    # get peer
    r = client.get(f"/vpn_peers/{peer['id']}", headers=headers)
    assert r.status_code == 200

    # list peers
    r = client.get("/vpn_peers/", headers=headers)
    assert r.status_code == 200

    # update peer
    upd = {"user_id": user["id"], "wg_public_key": "pubkey2", "wg_ip": "10.0.0.3/32"}
    r = client.put(f"/vpn_peers/{peer['id']}", json=upd, headers=headers)
    assert r.status_code == 200
    assert r.json()["wg_public_key"] == "pubkey2"

    # delete
    r = client.delete(f"/vpn_peers/{peer['id']}", headers=headers)
    assert r.status_code == 200
