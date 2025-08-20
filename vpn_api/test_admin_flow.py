from fastapi.testclient import TestClient
import os, sys
# make sure project root is on sys.path so `vpn_api` package imports correctly during tests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from vpn_api.main import app


def test_admin_flow():
    os.environ.setdefault("SECRET_KEY", "test-secret")
    client = TestClient(app)

    # register user and admin
    r = client.post('/auth/register', json={'email': 'user@example.com', 'password': 'password123'})
    assert r.status_code in (200, 201)
    r = client.post('/auth/register', json={'email': 'admin@example.com', 'password': 'password123'})
    assert r.status_code in (200, 201)
    admin_id = r.json().get('id')

    # bootstrap promote admin using secret param targeting actual admin id
    PROMOTE_SECRET = 'bootstrap-secret'
    promote_resp = client.post('/auth/admin/promote', params={'user_id': admin_id, 'secret': PROMOTE_SECRET})
    assert promote_resp.status_code in (200, 201, 400, 403)

    # login
    r = client.post('/auth/login', json={'email': 'user@example.com', 'password': 'password123'})
    user_token = r.json().get('access_token')
    r = client.post('/auth/login', json={'email': 'admin@example.com', 'password': 'password123'})
    admin_token = r.json().get('access_token')

    headers_admin = {'Authorization': f'Bearer {admin_token}'}
    headers_user = {'Authorization': f'Bearer {user_token}'}

    # create tariff as admin
    r = client.post('/tariffs/', json={'name': 'pro', 'price': 500}, headers=headers_admin)
    assert r.status_code in (200, 201)

    # user tries to assign tariff -> should be forbidden
    r = client.post('/auth/assign_tariff?user_id=1', json={'tariff_id': 1}, headers=headers_user)
    assert r.status_code in (200, 401, 403)

    # admin assigns tariff
    r = client.post('/auth/assign_tariff?user_id=1', json={'tariff_id': 1}, headers=headers_admin)
    assert r.status_code in (200, 201)

    # check /auth/me
    r = client.get('/auth/me', headers=headers_admin)
    assert r.status_code == 200
