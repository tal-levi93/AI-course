from datetime import datetime, timezone, timedelta

from app.security import generate_invite_token, hash_token
from app.models.invitation import Invitation


def test_invite_token_is_random_and_hashable():
    t1 = generate_invite_token()
    t2 = generate_invite_token()
    assert t1 != t2 and len(t1) >= 20
    assert hash_token(t1) == hash_token(t1)
    assert hash_token(t1) != t1


def _auth(client, email):
    client.post("/auth/register", json={"email": email, "password": "secret123", "display_name": email[:1]})
    t = client.post("/auth/login", json={"email": email, "password": "secret123"}).json()["access_token"]
    return {"Authorization": f"Bearer {t}"}


def test_owner_creates_invite_returns_token_and_url(client):
    owner = _auth(client, "io@b.com")
    hid = client.post("/households", json={"name": "Home"}, headers=owner).json()["id"]
    r = client.post(f"/households/{hid}/invitations", json={"email": "guest@b.com"}, headers=owner)
    assert r.status_code == 201
    body = r.json()
    assert body["token"] and body["accept_url"].endswith(body["token"])
    assert body["email"] == "guest@b.com"


def test_member_cannot_invite(client):
    owner = _auth(client, "io2@b.com")
    hid = client.post("/households", json={"name": "Home"}, headers=owner).json()["id"]
    guest = _auth(client, "stranger@b.com")
    r = client.post(f"/households/{hid}/invitations", json={"email": "x@b.com"}, headers=guest)
    assert r.status_code == 403


def test_list_and_revoke_invite(client):
    owner = _auth(client, "lr@b.com")
    hid = client.post("/households", json={"name": "Home"}, headers=owner).json()["id"]
    iid = client.post(f"/households/{hid}/invitations", json={"email": "g@b.com"}, headers=owner).json()["id"]
    lst = client.get(f"/households/{hid}/invitations", headers=owner).json()
    assert any(i["id"] == iid and i["status"] == "pending" for i in lst)
    assert client.delete(f"/households/{hid}/invitations/{iid}", headers=owner).status_code == 204
    lst2 = client.get(f"/households/{hid}/invitations", headers=owner).json()
    assert all(i["status"] != "pending" for i in lst2 if i["id"] == iid)


def _make_invite(client, owner_email, guest_email):
    owner = _auth(client, owner_email)
    hid = client.post("/households", json={"name": "Home"}, headers=owner).json()["id"]
    token = client.post(f"/households/{hid}/invitations", json={"email": guest_email}, headers=owner).json()["token"]
    return hid, token


def test_accept_with_matching_email_adds_member(client):
    hid, token = _make_invite(client, "a1@b.com", "guest1@b.com")
    guest = _auth(client, "guest1@b.com")
    r = client.post("/invitations/accept", json={"token": token}, headers=guest)
    assert r.status_code == 200 and r.json()["household_id"] == hid
    me = client.get("/auth/me", headers=guest).json()
    members = client.get(f"/households/{hid}/members", headers=guest).json()
    assert any(m["user_id"] == me["id"] and m["role"] == "member" for m in members)


def test_accept_with_wrong_email_rejected(client):
    hid, token = _make_invite(client, "a2@b.com", "guest2@b.com")
    wrong = _auth(client, "other@b.com")
    r = client.post("/invitations/accept", json={"token": token}, headers=wrong)
    assert r.status_code == 403


def test_accept_revoked_rejected(client):
    owner = _auth(client, "a3@b.com")
    hid = client.post("/households", json={"name": "Home"}, headers=owner).json()["id"]
    created = client.post(f"/households/{hid}/invitations", json={"email": "guest3@b.com"}, headers=owner).json()
    client.delete(f"/households/{hid}/invitations/{created['id']}", headers=owner)
    guest = _auth(client, "guest3@b.com")
    r = client.post("/invitations/accept", json={"token": created["token"]}, headers=guest)
    assert r.status_code == 400


def test_accept_already_accepted_rejected(client):
    hid, token = _make_invite(client, "a4@b.com", "guest4@b.com")
    guest = _auth(client, "guest4@b.com")
    assert client.post("/invitations/accept", json={"token": token}, headers=guest).status_code == 200
    r = client.post("/invitations/accept", json={"token": token}, headers=guest)
    assert r.status_code == 400


def test_accept_expired_rejected(client, db_session):
    hid, token = _make_invite(client, "a5@b.com", "guest5@b.com")
    inv = db_session.query(Invitation).first()
    inv.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    db_session.commit()
    guest = _auth(client, "guest5@b.com")
    r = client.post("/invitations/accept", json={"token": token}, headers=guest)
    assert r.status_code == 400
