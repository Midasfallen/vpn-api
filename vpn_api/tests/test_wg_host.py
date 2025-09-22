import subprocess
import types

from vpn_api import wg_host


def test_build_ssh_cmd_quoting():
    cmd = wg_host._build_ssh_cmd("root@host", "/path/script.sh", ["arg1", "a b"])
    assert "ssh" in cmd[0] or cmd[0] == "ssh"
    # ensure quoting preserved for second arg
    assert "a b" in " ".join(cmd)


def test_apply_remove_disabled(monkeypatch):
    # WG_APPLY_ENABLED is evaluated at import time; set module variable directly
    monkeypatch.setattr(wg_host, "WG_APPLY_ENABLED", False)

    class P:
        wg_public_key = "pk"

    assert wg_host.apply_peer(P()) is False
    assert wg_host.remove_peer(P()) is False


def test_apply_peer_success(monkeypatch):
    # WG_APPLY_ENABLED is evaluated at import time; set module variable directly
    monkeypatch.setattr(wg_host, "WG_APPLY_ENABLED", True)
    # Patch subprocess.run to simulate success
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: types.SimpleNamespace(returncode=0))

    class P:
        wg_public_key = "pk"

    assert wg_host.apply_peer(P()) is True


def test_generate_key_on_host_parsing(monkeypatch):
    monkeypatch.setattr(wg_host, "WG_APPLY_ENABLED", True)
    # simulate successful _run_and_capture output
    monkeypatch.setattr(
        wg_host, "_run_and_capture", lambda cmd: (0, "PRIVATE=/tmp/p\nPUBLIC=pubkey\n", "")
    )
    res = wg_host.generate_key_on_host("name", outdir="/tmp")
    assert res and res["public"] == "pubkey"
