import traceback
from typing import List

import aiohttp

# Minimal tracker for ClientSession instances created during tests.
_created: List[dict] = []


class TrackedClientSession(aiohttp.ClientSession):
    def __init__(self, *args, **kwargs):
        # capture stack where session was created
        stack = traceback.format_stack()[:-2]
        super().__init__(*args, **kwargs)
        self._tracker = {
            "closed": False,
            "stack": stack,
        }
        _created.append(self)

    def close(self):
        try:
            res = super().close()
            return res
        finally:
            if hasattr(self, "_tracker"):
                self._tracker["closed"] = True


def pytest_sessionstart(session):
    # patch aiohttp.ClientSession globally for tests
    aiohttp.ClientSession = TrackedClientSession  # type: ignore
    # If wg_easy_api already imported ClientSession at module import time,
    # patch its references as well so we can track sessions created there.
    try:
        import wg_easy_api.api as _wg_api

        if hasattr(_wg_api, "ClientSession"):
            _wg_api.ClientSession = TrackedClientSession  # type: ignore
    except Exception:
        # not installed or not imported yet; ignore
        pass
    try:
        import wg_easy_api.wg_easy as _wg_wg

        if hasattr(_wg_wg, "ClientSession"):
            _wg_wg.ClientSession = TrackedClientSession  # type: ignore
    except Exception:
        pass


def pytest_sessionfinish(session, exitstatus):
    import pytest as _pytest

    leaked = []
    for inst in list(_created):
        tr = getattr(inst, "_tracker", None)
        if tr and not tr.get("closed", True):
            leaked.append(tr)

    if leaked:
        msg_lines = ["Detected unclosed aiohttp.ClientSession instances:"]
        for i, tr in enumerate(leaked, 1):
            msg_lines.append(f"Leaked session #{i}, creation stack:")
            msg_lines.extend(tr["stack"])
        # Fail the test run so CI catches the regression
        _pytest.exit("\n".join(msg_lines), returncode=2)
