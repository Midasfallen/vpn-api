"""Debug script: register a test user and print the response.

Small helper for manual local testing. Not used in CI.
"""

import os

from fastapi.testclient import TestClient

from vpn_api.main import app

# ensure secret present like in conftest
os.environ.setdefault("SECRET_KEY", "test-secret")


client = TestClient(app)

resp = client.post(
    "/auth/register",
    json={"email": "debug@example.com", "password": "secretpass"},
)
print("status", resp.status_code)
try:
    print(resp.json())
except Exception:
    print(resp.text)
