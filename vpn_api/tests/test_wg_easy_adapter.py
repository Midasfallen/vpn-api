import pytest

from vpn_api.wg_easy_adapter import WgEasyAdapter


@pytest.mark.asyncio
async def test_adapter_context_manager(monkeypatch):
    # Create a fake WgEasy with minimal behaviour
    class FakeClient:
        def __init__(self, name, uid):
            self.name = name
            self.id = uid
            self.publicKey = "pubkey"

    class FakeWg:
        def __init__(self, url, password, session=None):
            self._clients = []

        async def login(self):
            return True

        async def create_client(self, name):
            self._clients.append(FakeClient(name, "cid-1"))

        async def get_clients(self):
            return self._clients

        async def delete_client(self, client_id):
            self._clients = [c for c in self._clients if c.id != client_id]

        async def get_client_config(self, client_id):
            return b"config"

    monkeypatch.setattr("vpn_api.wg_easy_adapter.WgEasy", FakeWg)

    async with WgEasyAdapter("http://127.0.0.1:51821", "pass") as adapter:
        result = await adapter.create_client("alice")
        assert result["id"] in ("cid-1",)
        assert result["publicKey"] == "pubkey"
        cfg = await adapter.get_client_config(result["id"])
        assert cfg == b"config"
        await adapter.delete_client(result["id"])
