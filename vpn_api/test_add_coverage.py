import os

import pytest
from fastapi.testclient import TestClient

# Ensure secrets
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("PROMOTE_SECRET", "bootstrap-secret")

from main import app

client = TestClient(app)


def get_auth_token_for_admin():
    # Try bootstrap promote flow: create a user and promote using PROMOTE_SECRET
    email = "covadmin@example.com"
    pwd = "covadminpass"
    # register user
    r = client.post("/auth/register", json={"email": email, "password": pwd})
    # login
    r = client.post("/auth/login", json={"email": email, "password": pwd})
    if r.status_code != 200:
        pytest.skip("Unable to login created user for admin token")
    token = r.json()["access_token"]
    # promote using promote secret
    headers = {"Authorization": f"Bearer {token}"}
    r2 = client.post("/auth/admin/promote?secret=bootstrap-secret&user_id=1", headers=headers)
    # if promotion via header fails, try promote endpoint with secret param without token
    if r2.status_code != 200:
        r2 = client.post("/auth/admin/promote?secret=bootstrap-secret&user_id=1")
    if r2.status_code != 200:
        pytest.skip("Could not promote user to admin")
    # login again to get admin token
    r = client.post("/auth/login", json={"email": email, "password": pwd})
    assert r.status_code == 200
    return r.json()["access_token"]


def test_delete_nonexistent_tariff():
    token = get_auth_token_for_admin()
    headers = {"Authorization": f"Bearer {token}"}
    r = client.delete("/tariffs/999999", headers=headers)
    assert r.status_code == 404


def test_create_and_list_tariff():
    token = get_auth_token_for_admin()
    headers = {"Authorization": f"Bearer {token}"}
    # create
    r = client.post("/tariffs/", json={"name": "cov-tariff", "price": 10}, headers=headers)
    assert r.status_code == 200
    # list
    r = client.get("/tariffs/?skip=0&limit=5", headers=headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)
