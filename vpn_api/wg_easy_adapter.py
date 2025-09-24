"""Simple adapter for wg-easy using the MIT-licensed `wg-easy-api` package.

This adapter exposes a small async API used by the rest of the project.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    # Import for type checkers only.
    from wg_easy_api import WgEasy  # type: ignore


# Module-level symbol expected by tests. Tests monkeypatch
# "vpn_api.wg_easy_adapter.WgEasy" so this name must exist at import
# time. It will be replaced in tests; at runtime we prefer a
# runtime import (see __aenter__) so we don't force the optional
# dependency at import time.
WgEasy = None


class WgEasyAdapter:
    def __init__(self, url: str, password: str, session=None):
        self.url = url
        self.password = password
        # Optional external client instance. Use a non-specific object type
        # at runtime to avoid confusing the type checker when tests monkeypatch
        # the module-level `WgEasy` symbol.
        self._wg: Optional[object] = None
        self._session = session

    async def __aenter__(self):
        # Prefer a module-level WgEasy symbol (tests monkeypatch this).
        # If not present, import the runtime package variant (WGEasy).
        try:
            _WgEasy = globals().get("WgEasy")
            if _WgEasy is None:
                # the package exports WGEasy (note uppercase GE) in some versions
                from wg_easy_api import WGEasy as _WgEasy  # type: ignore
        except Exception as e:
            raise RuntimeError("wg-easy-api package is not installed or failed to import") from e

        # instantiate with signature (base_url, password, session=None)
        # pass through configured session when available
        try:
            self._wg = _WgEasy(self.url, self.password, session=self._session)
        except TypeError:
            # fallback for wrappers that accept only (url, password)
            self._wg = _WgEasy(self.url, self.password)
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

    async def create_client(self, name: str) -> dict:  # noqa: C901
        """Create client and return server response (dict-like).

        The underlying wrapper typically returns a client model; we normalize
        to a dict with at least 'id' and 'publicKey' when available.
        """
        assert self._wg is not None, "adapter not started (use async context)"

        # Try using the underlying wrapper first (if available). If it fails
        # for any reason (network, server 500), fall back to a minimal HTTP
        # implementation that mirrors how the UI authenticates (POST /api/session
        # then POST /api/wireguard/client).
        last_exc: Optional[Exception] = None
        try:
            await self._wg.create_client(name)
            # get last created client by listing all and finding name
            clients = await self._wg.get_clients()
            for c in clients:
                if getattr(c, "name", None) == name:
                    return {
                        "id": getattr(c, "id", None) or getattr(c, "uid", None),
                        "publicKey": getattr(c, "publicKey", None)
                        or getattr(c, "public_key", None),
                    }
        except Exception as e:  # pragma: no cover - runtime fallback
            last_exc = e

        # Fallback: perform minimal HTTP requests using aiohttp and ALWAYS
        # authenticate using the Authorization header. Cookie/session-based
        # login is fragile here (the wg-easy server uses a per-process random
        # session secret), so prefer a header-based approach. If an API key
        # is configured in the environment as WG_API_KEY we send it as
        # "Bearer <key>", otherwise we send the plain password as the
        # header value (this mirrors how the UI server accepts raw password).
        try:
            import json as _json
            import os

            import aiohttp  # type: ignore

            base = self.url.rstrip("/")
            session = self._session or aiohttp.ClientSession()
            close_session = self._session is None

            async def _post(sess, url, json_payload=None, headers=None):
                resp = await sess.post(url, json=json_payload, headers=headers)
                text = await resp.text()
                return resp.status, text, resp

            async def _get(sess, url, headers=None):
                resp = await sess.get(url, headers=headers)
                text = await resp.text()
                return resp.status, text, resp

            # Build Authorization header: prefer WG_API_KEY if set.
            # NOTE: wg-easy server expects the raw key/password in the
            # Authorization header value (the server does not strip a
            # "Bearer " prefix), so we send the key directly.
            headers = {"Content-Type": "application/json"}
            api_key = os.environ.get("WG_API_KEY")
            if api_key:
                # send raw key (no 'Bearer ' prefix)
                headers["Authorization"] = api_key
            else:
                # fall back to plain password in header
                headers["Authorization"] = self.password

            create_url = f"{base}/api/wireguard/client"
            list_url = f"{base}/api/wireguard/client"

            if close_session:
                async with session as sess:
                    status, text, _resp = await _post(
                        sess, create_url, json_payload={"name": name}, headers=headers
                    )
                    if 200 <= status < 300:
                        _r_status, r_text, _r_resp = await _get(sess, list_url, headers=headers)
                        clients = _json.loads(r_text)
                        for c in clients:
                            if c.get("name") == name:
                                return {
                                    "id": c.get("id"),
                                    "publicKey": c.get("publicKey") or c.get("public_key"),
                                }
            else:
                sess = session
                status, text, _resp = await _post(
                    sess, create_url, json_payload={"name": name}, headers=headers
                )
                if 200 <= status < 300:
                    _r_status, r_text, _r_resp = await _get(sess, list_url, headers=headers)
                    clients = _json.loads(r_text)
                    for c in clients:
                        if c.get("name") == name:
                            return {
                                "id": c.get("id"),
                                "publicKey": c.get("publicKey") or c.get("public_key"),
                            }

            raise RuntimeError(f"wg-easy create client failed; last status={status}; body={text}")
        except Exception:  # pragma: no cover - runtime fallback
            # Prefer original exception context if available
            if last_exc is not None:
                raise RuntimeError("both wrapper and HTTP fallback failed") from last_exc
            raise

    async def delete_client(self, client_id: str) -> None:
        assert self._wg is not None, "adapter not started (use async context)"
        await self._wg.delete_client(client_id)

    async def get_client_config(self, client_id: str) -> bytes:
        assert self._wg is not None, "adapter not started (use async context)"
        return await self._wg.get_client_config(client_id)
