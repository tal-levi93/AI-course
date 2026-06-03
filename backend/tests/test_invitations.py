from app.security import generate_invite_token, hash_token


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
