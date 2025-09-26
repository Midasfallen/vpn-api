from unittest.mock import AsyncMock, MagicMock

import pytest

from vpn_api.wg_easy_adapter import WgEasyAdapter


@pytest.mark.asyncio
async def test_wrapper_session_closed_on_exit():
    # Create a fake wrapper that simulates having a session with close()
    class FakeWrapper:
        def __init__(self):
            self.session = MagicMock()

            # Make close() async or sync variations
            async def aclose():
                self.session.closed = True

            self.session.close = AsyncMock(side_effect=aclose)

        async def login(self):
            return True

        async def logout(self):
            return True

    adapter = WgEasyAdapter("http://example", "pw")
    fw = FakeWrapper()
    adapter._wg = fw

    # call __aexit__ directly to simulate context exit
    await adapter.__aexit__(None, None, None)

    # session.close should have been called and set closed marker
    assert getattr(fw.session, "closed", True) is True
