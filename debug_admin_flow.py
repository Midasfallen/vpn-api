import os
from fastapi.testclient import TestClient
os.environ.setdefault('SECRET_KEY','test-secret')
os.environ.setdefault('PROMOTE_SECRET','bootstrap-secret')
from vpn_api.main import app
from vpn_api.database import SessionLocal

client = TestClient(app)

r = client.post('/auth/register', json={'email':'user2@example.com','password':'password123'})
print('reg user', r.status_code, r.json())
r = client.post('/auth/register', json={'email':'admin2@example.com','password':'password123'})
print('reg admin', r.status_code, r.json())
prom = client.post('/auth/admin/promote', params={'user_id':2,'secret':'bootstrap-secret'})
print('promote', prom.status_code, prom.text)

# inspect DB
with SessionLocal() as s:
    users = s.query.__self__.registry
    # fallback: query via models
    from vpn_api import models
    us = s.query(models.User).all()
    print('users in db:')
    for u in us:
        print(u.id, u.email, u.is_admin)
