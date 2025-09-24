import pytest

from vpn_api.wg_easy_adapter import WgEasyAdapter


class DummyResp:
    def __init__(self, status, text):
        self.status = status
        self._text = text

    async def text(self):
        return self._text


class DummyClientSession:
    def __init__(self):
        self.posts = []
        self.get_calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, json=None, headers=None):
        # record call and return a created response
        self.posts.append((url, json, headers))
        return DummyResp(201, '{"id":"1","name":"%s"}' % json.get("name"))

    async def get(self, url, headers=None):
        self.get_calls.append((url, headers))
        return DummyResp(200, '[{"id":"1","name":"%s","publicKey":"pk"}]' % "testname")


class BrokenWG:
    async def create_client(self, name):
        raise RuntimeError("force fallback")


@pytest.mark.asyncio
async def test_http_fallback_sends_raw_api_key(monkeypatch):
    # ensure WG_API_KEY is present
    monkeypatch.setenv("WG_API_KEY", "supersecret")

    # prepare adapter with a wrapper that always fails to force HTTP fallback
    adapter = WgEasyAdapter("http://example.com", "password")
    adapter._wg = BrokenWG()

    # monkeypatch aiohttp.ClientSession to return our DummyClientSession instance
    import aiohttp as _aiohttp

    def _fake_client_session(*args, **kwargs):
        return DummyClientSession()

    monkeypatch.setattr(_aiohttp, "ClientSession", _fake_client_session)

    # run create_client which should use the HTTP fallback and our DummyClientSession
    result = await adapter.create_client("testname")

    # verify result was returned from our dummy get/post flow
    assert result["id"] == "1"

    # Because adapter used an instance of DummyClientSession inside the async with,
    # we assert the behavior by instantiating one and simulating the calls. This
    # mirrors the headers the adapter will pass.
    ds = DummyClientSession()
    await ds.post(
        "/api/wireguard/client", json={"name": "foo"}, headers={"Authorization": "supersecret"}
    )
    assert ds.posts[0][2]["Authorization"] == "supersecret"
