import os
from fastapi.testclient import TestClient
# ensure secret present like in conftest
os.environ.setdefault('SECRET_KEY', 'test-secret')
from vpn_api.main import app

client = TestClient(app)
resp = client.post('/auth/register', json={'email':'debug@example.com','password':'secretpass'})
print('status', resp.status_code)
try:
    print(resp.json())
except Exception:
    print(resp.text)
