import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vpn_api.wg_easy_adapter import WgEasyAdapter


@pytest.mark.asyncio
async def test_adapter_closes_internal_session(monkeypatch):
    # Simulate HTTP fallback: mock aiohttp.ClientSession so we can assert __aexit__/close
    mock_sess = AsyncMock()

    # mock post/get to return success and a client list containing our name
    async def fake_post(url, json=None, headers=None):
        m = MagicMock()
        m.status = 201

        async def text():
            return "{}"

        m.text = text
        return m

    async def fake_get(url, headers=None):
        m = MagicMock()
        m.status = 200

        async def text():
            return '[{"id": "cid", "name": "n1", "publicKey": "PK"}]'

        m.text = text
        return m

    mock_sess.post = AsyncMock(side_effect=fake_post)
    mock_sess.get = AsyncMock(side_effect=fake_get)

    # create a fake session object whose close() we can assert was awaited
    real_sess = MagicMock()
    real_sess.post = AsyncMock(side_effect=fake_post)
    real_sess.get = AsyncMock(side_effect=fake_get)
    real_sess.close = AsyncMock()

    class CM:
        def __init__(self, sess):
            self._sess = sess

        async def __aenter__(self):
            return self._sess

        async def __aexit__(self, exc_type, exc, tb):
            # adapter should close the session via context manager
            await self._sess.close()
            return False

    with patch("aiohttp.ClientSession", lambda *a, **k: CM(real_sess)):
        adapter = WgEasyAdapter("http://example", "pw")
        # force wrapper path to fail so code takes HTTP fallback
        adapter._wg = MagicMock()
        adapter._wg.create_client = AsyncMock(side_effect=Exception("force fallback"))
        result = await adapter.create_client("n1")
        assert result.get("id") == "cid"
        # ensure close() awaited
        real_sess.close.assert_awaited()


def test_adapter_does_not_close_external_session(monkeypatch):
    # Create a fake session with post/get and a close method we can track
    fake_sess = MagicMock()

    async def fake_post(url, json=None, headers=None):
        m = MagicMock()
        m.status = 201

        async def text():
            return "{}"

        m.text = text
        return m

    async def fake_get(url, headers=None):
        m = MagicMock()
        m.status = 200

        async def text():
            return '[{"id": "cid", "name": "n1", "publicKey": "PK"}]'

        m.text = text
        return m

    fake_sess.post = AsyncMock(side_effect=fake_post)
    fake_sess.get = AsyncMock(side_effect=fake_get)
    fake_sess.close = MagicMock()

    # Provide external session; adapter should not call close()
    adapter = WgEasyAdapter("http://example", "pw", session=fake_sess)
    # force wrapper to fail so fallback uses our provided session
    adapter._wg = MagicMock()
    adapter._wg.create_client = AsyncMock(side_effect=Exception("force fallback"))

    # Run inside event loop
    res = asyncio.get_event_loop().run_until_complete(adapter.create_client("n1"))
    assert res.get("id") == "cid"
    # external session close must not be called by adapter
    fake_sess.close.assert_not_called()
