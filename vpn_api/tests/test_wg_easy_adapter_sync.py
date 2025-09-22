import asyncio
import sys
import types

from vpn_api.wg_easy_adapter import WgEasyAdapter


def test_adapter_context_manager_sync(monkeypatch):
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

    # Ensure the adapter uses our fake implementation
    monkeypatch.setattr("vpn_api.wg_easy_adapter.WgEasy", FakeWg)

    async def run():
        async with WgEasyAdapter("http://127.0.0.1:51821", "pass") as adapter:
            result = await adapter.create_client("alice")
            assert result["id"] in ("cid-1",)
            assert result["publicKey"] == "pubkey"
            cfg = await adapter.get_client_config(result["id"])
            assert cfg == b"config"
            await adapter.delete_client(result["id"])

    asyncio.run(run())


def test_runtime_import_with_session(monkeypatch):
    # Create a fake wg_easy_api module with WGEasy that accepts session kw
    mod = types.SimpleNamespace()

    class WGEasyWithSession:
        def __init__(self, url, password, session=None):
            self.url = url
            self.password = password
            self.session = session
            self._clients = []

        async def login(self):
            return True

        async def create_client(self, name):
            self._clients.append(types.SimpleNamespace(name=name, id="cid-2", publicKey="pubkey"))

        async def get_clients(self):
            return self._clients

        async def delete_client(self, client_id):
            self._clients = [c for c in self._clients if c.id != client_id]

        async def get_client_config(self, client_id):
            return b"cfg2"

        async def logout(self):
            return True

    mod.WGEasy = WGEasyWithSession
    monkeypatch.setitem(sys.modules, "wg_easy_api", mod)
    # ensure module-level WgEasy is not interfering
    monkeypatch.setattr("vpn_api.wg_easy_adapter.WgEasy", None)

    async def run():
        async with WgEasyAdapter("http://x", "p", session=object()) as adapter:
            await adapter.create_client("bob")
            clients = await adapter._wg.get_clients()
            assert clients and clients[0].id == "cid-2"
            cfg = await adapter.get_client_config("cid-2")
            assert cfg == b"cfg2"

    asyncio.run(run())


def test_constructor_fallback_on_typeerror(monkeypatch):
    # WGEasy that does not accept session kw -> triggers TypeError then fallback
    mod = types.SimpleNamespace()

    class WGEasyNoSession:
        def __init__(self, url, password):
            self._clients = []

        async def login(self):
            return True

        async def create_client(self, name):
            self._clients.append(types.SimpleNamespace(name=name, id="cid-3", publicKey="pubkey"))

        async def get_clients(self):
            return self._clients

        async def delete_client(self, client_id):
            self._clients = [c for c in self._clients if c.id != client_id]

        async def get_client_config(self, client_id):
            return b"cfg3"

    mod.WGEasy = WGEasyNoSession
    monkeypatch.setitem(sys.modules, "wg_easy_api", mod)
    monkeypatch.setattr("vpn_api.wg_easy_adapter.WgEasy", None)

    async def run():
        async with WgEasyAdapter("http://x", "p", session=object()) as adapter:
            await adapter.create_client("carol")
            cfg = await adapter.get_client_config("cid-3")
            assert cfg == b"cfg3"

    asyncio.run(run())


def test_import_failure_raises_runtimeerror(monkeypatch):
    # Ensure no wg_easy_api present and module-level WgEasy None
    monkeypatch.setitem(sys.modules, "wg_easy_api", None)
    monkeypatch.setattr("vpn_api.wg_easy_adapter.WgEasy", None)

    async def run():
        try:
            async with WgEasyAdapter("http://x", "p"):
                pass
        except RuntimeError:
            return
        raise AssertionError("RuntimeError was not raised")

    asyncio.run(run())


def test_adapter_basic_sync_exercise(monkeypatch):
    # Simple fake client that lacks login/logout to cover branches
    class FakeClient:
        def __init__(self, name, uid):
            self.name = name
            self.id = uid
            self.publicKey = "p"

    class MinimalWg:
        def __init__(self, url, password, session=None):
            self._clients = []

        async def create_client(self, name):
            self._clients.append(FakeClient(name, "cid-x"))

        async def get_clients(self):
            return self._clients

        async def delete_client(self, client_id):
            self._clients = [c for c in self._clients if c.id != client_id]

        async def get_client_config(self, client_id):
            return b"x"

    monkeypatch.setattr("vpn_api.wg_easy_adapter.WgEasy", MinimalWg)

    async def run():
        async with WgEasyAdapter("u", "p") as adapter:
            r = await adapter.create_client("x")
            assert r["id"] == "cid-x"
            assert await adapter.get_client_config("cid-x") == b"x"
            await adapter.delete_client("cid-x")

    import asyncio

    asyncio.run(run())
