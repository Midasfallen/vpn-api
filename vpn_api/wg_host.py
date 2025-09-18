import logging
import os
import shlex
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)


WG_APPLY_ENABLED = os.getenv("WG_APPLY_ENABLED", "0") == "1"
WG_HOST_SSH = os.getenv("WG_HOST_SSH")  # e.g. root@62.84.98.109
WG_INTERFACE = os.getenv("WG_INTERFACE", "wg0")
WG_APPLY_SCRIPT = os.getenv("WG_APPLY_SCRIPT", "/srv/vpn-api/scripts/wg_apply.sh")
WG_REMOVE_SCRIPT = os.getenv("WG_REMOVE_SCRIPT", "/srv/vpn-api/scripts/wg_remove.sh")
WG_GEN_SCRIPT = os.getenv("WG_GEN_SCRIPT", "/srv/vpn-api/scripts/wg_gen_key.sh")


def _build_ssh_cmd(remote: str, script: str, args: list[str]) -> list[str]:
    # Quote args for remote shell
    remote_args = " ".join(shlex.quote(a) for a in args)
    cmd = ["ssh", remote, f"sudo {shlex.quote(script)} {remote_args}"]
    return cmd


def apply_peer(peer) -> bool:
    """Apply a peer to the WireGuard host. Returns True if the operation was attempted.

    This is a best-effort operation: DB changes are made before calling this function.
    If `WG_APPLY_ENABLED` is not set to '1', this function is a no-op and returns False.
    """
    if not WG_APPLY_ENABLED:
        logger.debug("WG apply disabled by env variable; skipping host apply")
        return False

    public = getattr(peer, "wg_public_key", None)
    allowed = getattr(peer, "allowed_ips", "") or ""
    iface = WG_INTERFACE

    args = [iface, public or "", allowed]

    try:
        if WG_HOST_SSH:
            cmd = _build_ssh_cmd(WG_HOST_SSH, WG_APPLY_SCRIPT, args)
        else:
            cmd = [WG_APPLY_SCRIPT, iface, public or "", allowed]

        logger.info("Applying WireGuard peer on host: %s", cmd)
        subprocess.run(cmd, check=True, capture_output=True)
        logger.info("WireGuard peer applied successfully")
        return True
    except Exception as exc:
        logger.exception("Failed to apply WireGuard peer on host: %s", exc)
        return False


def remove_peer(peer) -> bool:
    if not WG_APPLY_ENABLED:
        logger.debug("WG remove disabled by env variable; skipping host remove")
        return False

    public = getattr(peer, "wg_public_key", None)
    iface = WG_INTERFACE
    args = [iface, public or ""]

    try:
        if WG_HOST_SSH:
            cmd = _build_ssh_cmd(WG_HOST_SSH, WG_REMOVE_SCRIPT, args)
        else:
            cmd = [WG_REMOVE_SCRIPT, iface, public or ""]

        logger.info("Removing WireGuard peer on host: %s", cmd)
        subprocess.run(cmd, check=True, capture_output=True)
        logger.info("WireGuard peer removed successfully")
        return True
    except Exception as exc:
        logger.exception("Failed to remove WireGuard peer on host: %s", exc)
        return False


def _run_and_capture(cmd: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def generate_key_on_host(base_name: str, outdir: str = "/etc/wg-keys") -> Optional[dict]:
    """Generate keypair on host and return {'private': path, 'public': pubkey} or None."""
    if not WG_APPLY_ENABLED:
        logger.debug("WG key generation disabled by env variable; skipping host gen")
        return None

    args = [outdir, base_name]
    try:
        if WG_HOST_SSH:
            cmd = _build_ssh_cmd(WG_HOST_SSH, WG_GEN_SCRIPT, args)
        else:
            cmd = [WG_GEN_SCRIPT, outdir, base_name]

        logger.info("Generating WireGuard keys on host: %s", cmd)
        code, out, err = _run_and_capture(cmd)
        if code != 0:
            logger.error("Key generation failed: %s", err)
            return None

        # parse output lines like PRIVATE=/path and PUBLIC=<pubkey>
        result = {}
        for line in out.splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                result[k.strip().lower()] = v.strip()

        if "private" in result and "public" in result:
            return {"private": result["private"], "public": result["public"]}
        logger.error("Unexpected keygen output: %s", out)
        return None
    except Exception as exc:
        logger.exception("Failed to generate key on host: %s", exc)
        return None
