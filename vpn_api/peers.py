import asyncio
import os
import secrets
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from vpn_api import models, schemas
from vpn_api.auth import get_current_user
from vpn_api.database import get_db
from vpn_api.wg_easy_adapter import WgEasyAdapter
from vpn_api.wg_host import apply_peer, generate_key_on_host, remove_peer

router = APIRouter(prefix="/vpn_peers", tags=["vpn_peers"])


@router.post("/", response_model=schemas.VpnPeerOut)
def create_peer(
    payload: schemas.VpnPeerCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # only admin or the same user can create peer
    if not getattr(current_user, "is_admin", False) and current_user.id != payload.user_id:
        raise HTTPException(status_code=403, detail="Not allowed")
    # decide key policy: default keep key in DB; alternative 'host' generates key on host
    key_policy = os.getenv("WG_KEY_POLICY", "db")
    private = secrets.token_urlsafe(32)
    public = payload.wg_public_key

    if key_policy == "host":
        # attempt to generate keypair on host; use username or timestamp as base name
        base = f"peer_{payload.user_id}_{secrets.token_hex(6)}"
        gen = generate_key_on_host(base)
        if gen:
            private = f"host:{gen['private']}"
            public = gen["public"]
    elif key_policy == "wg-easy":
        # Use the wg-easy HTTP API (via adapter). Create remote client first
        # then persist DB row. If persisting fails we attempt to delete the
        # remote client to avoid orphaned peers.
        try:
            public, private, wg_client_id = _handle_wg_easy_creation(payload.user_id)
        except Exception as e:
            raise HTTPException(
                status_code=502, detail=f"failed to create remote wg-easy client: {e}"
            ) from e

    peer = models.VpnPeer(
        user_id=payload.user_id,
        wg_private_key=private,
        wg_public_key=public,
        wg_client_id=locals().get("wg_client_id"),
        wg_ip=payload.wg_ip,
        allowed_ips=payload.allowed_ips,
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
    return peer


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


def _handle_wg_easy_creation(user_id: int):
    """Create a wg-easy client for given user and return (public, private, id).

    Raises HTTPException if required env vars are missing.
    """
    wg_url = os.getenv("WG_EASY_URL")
    wg_pass = os.getenv("WG_EASY_PASSWORD")
    if not wg_url or not wg_pass:
        raise HTTPException(status_code=500, detail="WG_EASY_URL or WG_EASY_PASSWORD not set")

    created = _create_wg_easy_client(wg_url, wg_pass, f"peer-{user_id}-{secrets.token_hex(4)}")
    public = created.get("publicKey")
    wg_client_id = created.get("id")
    private = "wg-easy:remote"
    return public, private, wg_client_id


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
