"""Simple adapter for wg-easy using the MIT-licensed `wg-easy-api` package.

This adapter exposes a small async API used by the rest of the project.
"""

from __future__ import annotations

from typing import Optional

try:
    from wg_easy_api import WgEasy
except Exception:  # pragma: no cover - optional dependency
    WgEasy = None


class WgEasyAdapter:
    def __init__(self, url: str, password: str, session=None):
        self.url = url
        self.password = password
        self._wg: Optional[WgEasy] = None
        self._session = session

    async def __aenter__(self):
        self._wg = WgEasy(self.url, self.password, self._session)
        # some wrappers provide login inside context manager; ensure login
        if hasattr(self._wg, "login"):
            await self._wg.login()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        # best-effort logout/close
        try:
            if self._wg is not None and hasattr(self._wg, "logout"):
                await self._wg.logout()
        finally:
            self._wg = None

    async def create_client(self, name: str) -> dict:
        """Create client and return server response (dict-like).

        The underlying wrapper typically returns a client model; we normalize
        to a dict with at least 'id' and 'publicKey' when available.
        """
        assert self._wg is not None, "adapter not started (use async context)"
        await self._wg.create_client(name)
        # get last created client by listing all and finding name
        clients = await self._wg.get_clients()
        for c in clients:
            if getattr(c, "name", None) == name:
                return {
                    "id": getattr(c, "id", None) or getattr(c, "uid", None),
                    "publicKey": getattr(c, "publicKey", None) or getattr(c, "public_key", None),
                }
        raise RuntimeError("failed to find created client")

    async def delete_client(self, client_id: str) -> None:
        assert self._wg is not None, "adapter not started (use async context)"
        await self._wg.delete_client(client_id)

    async def get_client_config(self, client_id: str) -> bytes:
        assert self._wg is not None, "adapter not started (use async context)"
        return await self._wg.get_client_config(client_id)
