from fastapi.testclient import TestClient
from vpn_api.main import app

client = TestClient(app)


def test_payments_crud_flow():
    # register a user
    r = client.post('/auth/register', json={'email':'pay@example.com','password':'strongpass'})
    assert r.status_code == 200
    user = r.json()
    # bootstrap promote to admin
    r = client.post('/auth/admin/promote', params={'user_id': user['id'], 'secret': 'bootstrap-secret'})
    assert r.status_code in (200,201,204,403)
    # login
    r = client.post('/auth/login', json={'email':'pay@example.com','password':'strongpass'})
    assert r.status_code == 200
    token = r.json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}

    # create payment as admin for user
    payload = {'user_id': user['id'], 'amount': 5.50, 'currency':'USD', 'provider':'manual'}
    r = client.post('/payments/', json=payload, headers=headers)
    assert r.status_code == 200
    payment = r.json()
    assert float(payment['amount']) == 5.5

    # get payment
    r = client.get(f"/payments/{payment['id']}", headers=headers)
    assert r.status_code == 200

    # list payments
    r = client.get('/payments/', headers=headers)
    assert r.status_code == 200

    # update payment
    upd = {'user_id': user['id'], 'amount': 10.00, 'currency':'USD', 'provider':'manual'}
    r = client.put(f"/payments/{payment['id']}", json=upd, headers=headers)
    assert r.status_code == 200
    assert float(r.json()['amount']) == 10.0

    # delete
    r = client.delete(f"/payments/{payment['id']}", headers=headers)
    assert r.status_code == 200
