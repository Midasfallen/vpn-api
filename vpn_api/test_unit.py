
import os
os.environ["SECRET_KEY"] = "testsecretkey"
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_register_and_login():
    email = "unituser@example.com"
    password = "unitpass123"
    # Регистрация
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code == 200 or (r.status_code == 400 and "already registered" in r.text)
    # Логин
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200
    token = r.json()["access_token"]
    assert token

def test_tariff_crud():
    # Логин админа (должен быть создан заранее)
    email = "admin@example.com"
    password = "adminpass123"
    r = client.post("/auth/login", json={"email": email, "password": password})
    if r.status_code != 200:
        pytest.skip("Admin user not available")
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    # Создание тарифа
    r = client.post("/tariffs/", json={"name": "unit-tariff", "price": 123}, headers=headers)
    assert r.status_code == 200 or (r.status_code == 400 and "already exists" in r.text)
    # Пагинация
    r = client.get("/tariffs/?skip=0&limit=2", headers=headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)
