import os
import sys

import pytest
from fastapi.testclient import TestClient

# make sure project root is on sys.path so `vpn_api` package imports correctly during tests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from vpn_api.main import app


@pytest.mark.skip(reason="Endpoint /auth/assign_tariff not implemented yet")
def test_basic_flow():
    os.environ.setdefault("SECRET_KEY", "test-secret")
    client = TestClient(app)

    # register
    r = client.post("/auth/register", json={"email": "test@example.com", "password": "secretpass"})
    assert r.status_code in (200, 201)

    # login
    r = client.post("/auth/login", json={"email": "test@example.com", "password": "secretpass"})
    assert r.status_code == 200
    token = r.json().get("access_token")
    assert token

    headers = {"Authorization": f"Bearer {token}"}

    # create tariff
    r2 = client.post("/tariffs/", json={"name": "basic", "price": 100}, headers=headers)
    assert r2.status_code in (200, 201)

    # assign tariff (user is not admin) -> should be forbidden
    r3 = client.post("/auth/assign_tariff?user_id=1", json={"tariff_id": 1}, headers=headers)
    assert r3.status_code == 403

    # me (user may still be inactive because only assigning a tariff as admin activates)
    r4 = client.get("/auth/me", headers=headers)
    assert r4.status_code in (200, 403)
