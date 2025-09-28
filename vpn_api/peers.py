import asyncio
import os
import secrets
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from vpn_api import models, schemas
from vpn_api.auth import get_current_user
from vpn_api.crypto import decrypt_text, encrypt_text
from vpn_api.database import get_db
from vpn_api.wg_easy_adapter import WgEasyAdapter
from vpn_api.wg_host import apply_peer, generate_key_on_host, remove_peer

router = APIRouter(prefix="/vpn_peers", tags=["vpn_peers"])


def _alloc_dummy_ip(user_id: int) -> str:
    """Allocate a deterministic dummy /32 address in 10.10.x.y range for tests.

    This is intentionally simple: use low bytes of a token combined with user id
    to avoid collisions in unit tests. Not intended for production use.
    """
    # Use a short token to add entropy
    tok = secrets.token_hex(2)
    # derive two octets from token+user_id
    a = (user_id + int(tok[:2], 16)) % 250 + 1
    b = (int(tok[2:], 16) + user_id) % 250 + 1
    return f"10.10.{a}.{b}/32"


@router.post("/", response_model=schemas.VpnPeerOut)
def create_peer(  # noqa: C901 - function is intentionally a bit complex; refactor in follow-up
    payload: schemas.VpnPeerCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):

    # only admin or the same user can create peer
    # decide target user: default to authenticated user when not provided
    target_user = payload.user_id or current_user.id
    # only admin or the same user can create peer
    if not getattr(current_user, "is_admin", False) and current_user.id != target_user:
        raise HTTPException(status_code=403, detail="Not allowed")
    # decide key policy: default keep key in DB; alternative 'host' generates key on host
    key_policy = os.getenv("WG_KEY_POLICY", "db")
    private = secrets.token_urlsafe(32)
    public = payload.wg_public_key
    # container for any metadata returned by external controllers
    extra_metadata: dict = {}

    # For db-backed keys, ensure we have a public key placeholder and an IP
    # so DB constraints are satisfied when tests provide a minimal payload.
    if key_policy == "db":
        if not public:
            public = f"db:{secrets.token_urlsafe(16)}"
        if not payload.wg_ip:
            payload.wg_ip = _alloc_dummy_ip(target_user)

    if key_policy == "host":
        # attempt to generate keypair on host; use username or timestamp as base name
        base = f"peer_{target_user}_{secrets.token_hex(6)}"
        gen = generate_key_on_host(base)
        if gen:
            private = f"host:{gen['private']}"
            public = gen["public"]
        # ensure wg_ip exists to satisfy DB NOT NULL; allocate a synthetic
        # address when not provided by payload or controller
        if not payload.wg_ip:
            payload.wg_ip = _alloc_dummy_ip(target_user)
    elif key_policy == "wg-easy":
        # Use the wg-easy HTTP API (via adapter). Create remote client first
        # then persist DB row. If persisting fails we attempt to delete the
        # remote client to avoid orphaned peers.
        try:
            # Create client and also attempt to retrieve client config. If the
            # incoming payload omitted wg_public_key or wg_ip we will fill them
            # from the controller response.
            public, private, wg_client_id, meta = _handle_wg_easy_creation(
                target_user, payload.device_name
            )
            extra_metadata.update(meta or {})
            # If wg_ip missing in payload, try to obtain from metadata
            if not payload.wg_ip:
                payload.wg_ip = extra_metadata.get("address")
            if not payload.allowed_ips:
                payload.allowed_ips = extra_metadata.get("allowed_ips")
        except Exception as e:
            raise HTTPException(
                status_code=502, detail=f"failed to create remote wg-easy client: {e}"
            ) from e

    peer = models.VpnPeer(
        user_id=target_user,
        wg_private_key=private,
        wg_public_key=public,
        wg_client_id=locals().get("wg_client_id"),
        wg_ip=payload.wg_ip or extra_metadata.get("address"),
        allowed_ips=payload.allowed_ips or extra_metadata.get("allowed_ips"),
        # If we generated a wg-quick config from the controller or local keys,
        # attempt to persist an encrypted copy so clients can fetch it later.
        wg_config_encrypted=None,
    )
    db.add(peer)
    try:
        db.commit()
        db.refresh(peer)
    except Exception:
        # If we created a remote wg-easy client above, remove it as
        # compensation to avoid orphaned entries.
        try:
            if locals().get("wg_client_id"):
                _delete_wg_easy_client(
                    os.getenv("WG_EASY_URL"),
                    os.getenv("WG_EASY_PASSWORD"),
                    locals().get("wg_client_id"),
                )
        except Exception:
            # best-effort
            pass
        raise
    # Try to apply the peer on the host (best-effort). This will be a no-op unless
    # WG_APPLY_ENABLED=1 is set in the environment. We don't fail the API call if
    # the host operation fails; the DB remains the source of truth.
    try:
        apply_peer(peer)
    except Exception:
        # apply_peer is already logging; swallow exceptions to avoid 500s
        pass
    # Attach any extra metadata onto the returned model object for the
    # response serializer to include (e.g. dns/endpoint). We intentionally
    # don't persist unrelated controller fields to the DB schema here.
    for k, v in extra_metadata.items():
        setattr(peer, k, v)
    # If key policy produced a config (wg-easy path or local generation), try
    # to store the wg-quick client config encrypted in the DB (best-effort).
    try:
        # If wg-easy created a config, _get_wg_easy_client_config may have
        # returned metadata including the private key; build a wg-quick text
        # when possible.
        cfg_text = None
        if locals().get("wg_client_id"):
            # attempt to fetch the config again (best-effort, synchronous)
            try:
                cfg_bytes = _get_wg_easy_client_config(
                    os.getenv("WG_EASY_URL"),
                    os.getenv("WG_EASY_PASSWORD"),
                    locals().get("wg_client_id"),
                )
                cfg_text = (
                    cfg_bytes.decode("utf-8")
                    if isinstance(cfg_bytes, (bytes, bytearray))
                    else str(cfg_bytes)
                )
            except Exception:
                cfg_text = None
        else:
            # For db or host keys generate a minimal wg-quick client config from
            # the stored values so that the mobile app can import it.
            if getattr(peer, "wg_private_key", None) and getattr(peer, "wg_public_key", None):
                # Build a minimal config
                cfg_text = (
                    "[Interface]\n"
                    f"PrivateKey = {peer.wg_private_key}\n"
                    f"Address = {peer.wg_ip}\n\n"
                    "[Peer]\n"
                    f"PublicKey = {peer.wg_public_key}\n"
                    f"AllowedIPs = {peer.allowed_ips or '0.0.0.0/0'}\n"
                )
        if cfg_text:
            enc = encrypt_text(cfg_text)
            peer.wg_config_encrypted = enc
            db.add(peer)
            db.commit()
            db.refresh(peer)
    except Exception:
        # best-effort; do not fail the API call if persistence of encrypted
        # config fails.
        pass
    return peer


@router.get("/self/config")
def get_my_peer_config(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    """Return the decrypted wg-quick configuration for the authenticated user's peer.

    This endpoint requires authentication and returns the plaintext wg-quick config
    so the mobile client can programmatically import and start WireGuard.
    """
    # Find the active peer for the user (pick most recent active)
    peer = (
        db.query(models.VpnPeer)
        .filter(models.VpnPeer.user_id == current_user.id, models.VpnPeer.active)
        .order_by(models.VpnPeer.created_at.desc())
        .first()
    )
    if not peer:
        raise HTTPException(status_code=404, detail="No peer found for user")
    if not peer.wg_config_encrypted:
        raise HTTPException(status_code=404, detail="No stored config for peer")
    cfg = decrypt_text(peer.wg_config_encrypted)
    if cfg is None:
        raise HTTPException(status_code=500, detail="failed to decrypt stored config")
    return {"wg_quick": cfg}


def _create_wg_easy_client(url: str, password: str, name: str) -> dict:
    """Call the async WgEasyAdapter.create_client synchronously and return result."""

    async def _inner():
        async with WgEasyAdapter(url, password) as adapter:
            return await adapter.create_client(name)

    return asyncio.run(_inner())


def _delete_wg_easy_client(url: str, password: str, client_id: str) -> None:
    async def _inner():
        async with WgEasyAdapter(url, password) as adapter:
            await adapter.delete_client(client_id)

    return asyncio.run(_inner())


def _parse_wg_quick_config(cfg_text: str) -> dict:
    """Parse a wg-quick style client config and return metadata.

    Returns keys: address, allowed_ips, dns, endpoint, private_key
    """
    meta = {}
    current = None
    for line in cfg_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("["):
            current = line.strip("[]").lower()
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            meta_key = f"{current}.{k.strip().lower()}" if current else k.strip().lower()
            meta[meta_key] = v.strip()

    # Normalize common fields
    result = {}
    # client Address under Interface
    result["address"] = meta.get("interface.address") or meta.get("address")
    # AllowedIPs under Peer
    result["allowed_ips"] = (
        meta.get("peer.allowedips") or meta.get("allowedips") or meta.get("allowed_ips")
    )
    result["dns"] = meta.get("interface.dns") or meta.get("dns")
    result["endpoint"] = meta.get("peer.endpoint") or meta.get("endpoint")
    result["private_key"] = (
        meta.get("interface.privatekey") or meta.get("privatekey") or meta.get("private_key")
    )
    return result


def _handle_wg_easy_creation(user_id: int, device_name: str | None = None):
    """Create a wg-easy client for given user and return (public, private, id).

    Raises HTTPException if required env vars are missing.
    """
    wg_url = os.getenv("WG_EASY_URL")
    wg_pass = os.getenv("WG_EASY_PASSWORD")
    if not wg_url or not wg_pass:
        raise HTTPException(status_code=500, detail="WG_EASY_URL or WG_EASY_PASSWORD not set")

    name = device_name or f"peer-{user_id}-{secrets.token_hex(4)}"
    created = _create_wg_easy_client(wg_url, wg_pass, name)
    public = created.get("publicKey")
    wg_client_id = created.get("id")
    # Attempt to fetch client config (wg-quick) to extract private key and IPs
    try:
        cfg_bytes = _get_wg_easy_client_config(wg_url, wg_pass, wg_client_id)
        cfg_text = (
            cfg_bytes.decode("utf-8")
            if isinstance(cfg_bytes, (bytes, bytearray))
            else str(cfg_bytes)
        )
        meta = _parse_wg_quick_config(cfg_text)
        private = meta.get("private_key") or "wg-easy:remote"
        # If public key not present try to derive from config (rare)
        return public, private, wg_client_id, meta
    except Exception:
        return public, "wg-easy:remote", wg_client_id, {}


def _get_wg_easy_client_config(url: str, password: str, client_id: str) -> bytes:
    # Prefer a simple synchronous HTTP GET here to avoid creating an
    # aiohttp.ClientSession in a library (wg_easy_api) when called from
    # synchronous code paths (tests and API helpers). The caller will
    # treat any exception as non-fatal and fall back to a placeholder.
    try:
        import urllib.request

        base = url.rstrip("/")
        cfg_url = f"{base}/api/wireguard/client/{client_id}/configuration"
        # Build Authorization header: prefer WG_API_KEY if set.
        api_key = os.environ.get("WG_API_KEY")
        if api_key:
            auth = api_key
        else:
            auth = password

        req = urllib.request.Request(cfg_url, headers={"Authorization": auth})
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.read()
    except Exception:
        # Caller handles failures; return empty bytes to indicate missing config
        raise


@router.get("/", response_model=List[schemas.VpnPeerOut])
def list_peers(
    user_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    q = db.query(models.VpnPeer)
    if user_id:
        # non-admin can only list their own
        if not getattr(current_user, "is_admin", False) and current_user.id != user_id:
            raise HTTPException(status_code=403, detail="Not allowed")
        q = q.filter(models.VpnPeer.user_id == user_id)
    elif not getattr(current_user, "is_admin", False):
        q = q.filter(models.VpnPeer.user_id == current_user.id)
    return q.offset(skip).limit(limit).all()


@router.get("/{peer_id}", response_model=schemas.VpnPeerOut)
def get_peer(
    peer_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    peer = db.query(models.VpnPeer).filter(models.VpnPeer.id == peer_id).first()
    if not peer:
        raise HTTPException(status_code=404, detail="Peer not found")
    if not getattr(current_user, "is_admin", False) and peer.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    # For security: never return the private key via GET endpoints. Only the
    # create endpoint will return the private key once (if available).
    try:
        peer.wg_private_key = None
    except Exception:
        pass
    return peer


@router.post(
    "/self",
    response_model=schemas.VpnPeerOut,
    summary="Create a VPN peer for the authenticated user",
    description=(
        "Create a WireGuard peer for the current authenticated user. If keys or IP are omitted,\n"
        "the server will allocate them according to WG_KEY_POLICY (db/host/wg-easy).\n"
        "Returned object includes the private key once so the client can configure its\n"
        "local interface."
    ),
    responses={
        200: {
            "description": "Peer created",
            "content": {
                "application/json": {
                    "example": {
                        "id": 6,
                        "user_id": 40,
                        "wg_public_key": "db:abc123...",
                        "wg_private_key": "priv:xxx",
                        "wg_ip": "10.10.75.66/32",
                        "allowed_ips": None,
                        "active": True,
                        "created_at": "2025-09-28T12:34:56Z",
                    }
                }
            },
        },
        403: {"description": "Not allowed / user not active"},
    },
)
def create_peer_self(
    payload: schemas.VpnPeerCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Force the payload user to the current user and reuse create_peer logic.
    payload.user_id = current_user.id
    peer = create_peer(payload, db=db, current_user=current_user)
    # create_peer may have attached wg_private_key into the model; return as-is
    return peer


@router.put("/{peer_id}", response_model=schemas.VpnPeerOut)
def update_peer(
    peer_id: int,
    payload: schemas.VpnPeerCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    peer = db.query(models.VpnPeer).filter(models.VpnPeer.id == peer_id).first()
    if not peer:
        raise HTTPException(status_code=404, detail="Peer not found")
    if not getattr(current_user, "is_admin", False) and peer.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    peer.wg_public_key = payload.wg_public_key
    peer.wg_ip = payload.wg_ip
    peer.allowed_ips = payload.allowed_ips
    db.commit()
    db.refresh(peer)
    return peer


@router.delete("/{peer_id}")
def delete_peer(
    peer_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    peer = db.query(models.VpnPeer).filter(models.VpnPeer.id == peer_id).first()
    if not peer:
        raise HTTPException(status_code=404, detail="Peer not found")
    if not getattr(current_user, "is_admin", False) and peer.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    db.delete(peer)
    db.commit()
    # Best-effort remove from host or wg-easy controller
    try:
        # If peer was created via wg-easy remove remote client id as well
        if getattr(peer, "wg_client_id", None):
            try:
                _delete_wg_easy_client(
                    os.getenv("WG_EASY_URL"), os.getenv("WG_EASY_PASSWORD"), peer.wg_client_id
                )
            except Exception:
                pass
        remove_peer(peer)
    except Exception:
        pass
    return {"msg": "deleted"}
