import pytest

from vpn_api import models, peers, schemas
from vpn_api.database import Base, SessionLocal, engine


def setup_module():
    # Ensure tables exist for test DB (conftest sets DEV_INIT_DB)
    Base.metadata.create_all(bind=engine)


def test_create_peer_wg_easy_success(monkeypatch):
    calls = {}
    # Ensure code chooses wg-easy path
    monkeypatch.setenv("WG_KEY_POLICY", "wg-easy")
    monkeypatch.setenv("WG_EASY_URL", "http://127.0.0.1:51821")
    monkeypatch.setenv("WG_EASY_PASSWORD", "pass")

    def fake_create(url, password, name):
        calls["created"] = {"id": "cid-1", "publicKey": "pubkey"}
        return calls["created"]

    def fake_delete(url, password, cid):
        calls.setdefault("deleted", []).append(cid)

    monkeypatch.setattr(peers, "_create_wg_easy_client", fake_create)
    monkeypatch.setattr(peers, "_delete_wg_easy_client", fake_delete)

    db = SessionLocal()
    # create user
    user = models.User(email="u@example.test")
    db.add(user)
    db.commit()
    db.refresh(user)

    payload = schemas.VpnPeerCreate(
        user_id=user.id, wg_public_key="", wg_ip="10.0.0.5", allowed_ips="10.0.0.5/32"
    )

    # call create_peer (sync) as if current_user is same user
    peer = peers.create_peer(payload, db=db, current_user=user)
    assert peer.wg_client_id == "cid-1"
    assert peer.wg_public_key == "pubkey"


def test_create_peer_wg_easy_compensate_on_db_failure(monkeypatch):
    created = {"id": "cid-2", "publicKey": "pubkey2"}
    deleted = []
    monkeypatch.setenv("WG_KEY_POLICY", "wg-easy")
    monkeypatch.setenv("WG_EASY_URL", "http://127.0.0.1:51821")
    monkeypatch.setenv("WG_EASY_PASSWORD", "pass")

    def fake_create(url, password, name):
        return created

    def fake_delete(url, password, cid):
        deleted.append(cid)

    monkeypatch.setattr(peers, "_create_wg_easy_client", fake_create)
    monkeypatch.setattr(peers, "_delete_wg_easy_client", fake_delete)

    db = SessionLocal()
    user = models.User(email="u2@example.test")
    db.add(user)
    db.commit()
    db.refresh(user)

    payload = schemas.VpnPeerCreate(
        user_id=user.id, wg_public_key="", wg_ip="10.0.0.6", allowed_ips="10.0.0.6/32"
    )

    # monkeypatch commit to raise to simulate DB failure
    def bad_commit():
        raise Exception("db commit failed")

    db.commit = bad_commit

    with pytest.raises(RuntimeError):
        peers.create_peer(payload, db=db, current_user=user)

    # ensure compensation attempted: remote client deleted
    assert deleted == [created["id"]]
