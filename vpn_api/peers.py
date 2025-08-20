from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import secrets

from vpn_api import models, schemas
from vpn_api.database import get_db
from vpn_api.auth import get_current_user

router = APIRouter(prefix="/vpn_peers", tags=["vpn_peers"])


@router.post("/", response_model=schemas.VpnPeerOut)
def create_peer(payload: schemas.VpnPeerCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # only admin or the same user can create peer
    if not getattr(current_user, "is_admin", False) and current_user.id != payload.user_id:
        raise HTTPException(status_code=403, detail="Not allowed")
    # generate private key placeholder
    private = secrets.token_urlsafe(32)
    peer = models.VpnPeer(user_id=payload.user_id, wg_private_key=private, wg_public_key=payload.wg_public_key, wg_ip=payload.wg_ip, allowed_ips=payload.allowed_ips)
    db.add(peer)
    db.commit()
    db.refresh(peer)
    return peer


@router.get("/", response_model=List[schemas.VpnPeerOut])
def list_peers(user_id: Optional[int] = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
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
def get_peer(peer_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    peer = db.query(models.VpnPeer).filter(models.VpnPeer.id == peer_id).first()
    if not peer:
        raise HTTPException(status_code=404, detail="Peer not found")
    if not getattr(current_user, "is_admin", False) and peer.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    return peer


@router.put("/{peer_id}", response_model=schemas.VpnPeerOut)
def update_peer(peer_id: int, payload: schemas.VpnPeerCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
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
def delete_peer(peer_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    peer = db.query(models.VpnPeer).filter(models.VpnPeer.id == peer_id).first()
    if not peer:
        raise HTTPException(status_code=404, detail="Peer not found")
    if not getattr(current_user, "is_admin", False) and peer.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    db.delete(peer)
    db.commit()
    return {"msg": "deleted"}
