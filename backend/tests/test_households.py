from app.models.user import User
from app.models.household import Household, Membership


def test_membership_unique(db_session):
    u = User(email="o@b.com", password_hash="x", display_name="O")
    db_session.add(u); db_session.commit()
    h = Household(name="Home", owner_id=u.id)
    db_session.add(h); db_session.commit()
    m = Membership(household_id=h.id, user_id=u.id, role="owner")
    db_session.add(m); db_session.commit()
    assert m.id is not None
    assert m.role == "owner"


def _auth(client, email):
    client.post("/auth/register", json={"email": email, "password": "secret123", "display_name": email[:1]})
    t = client.post("/auth/login", json={"email": email, "password": "secret123"}).json()["access_token"]
    return {"Authorization": f"Bearer {t}"}

def test_create_household_makes_owner(client):
    h = _auth(client, "owner@b.com")
    r = client.post("/households", json={"name": "Home"}, headers=h)
    assert r.status_code == 201
    hid = r.json()["id"]
    members = client.get(f"/households/{hid}/members", headers=h).json()
    assert len(members) == 1 and members[0]["role"] == "owner"

def test_list_my_households(client):
    h = _auth(client, "owner2@b.com")
    client.post("/households", json={"name": "A"}, headers=h)
    client.post("/households", json={"name": "B"}, headers=h)
    r = client.get("/households", headers=h)
    assert r.status_code == 200 and len(r.json()) == 2

def test_rename_requires_owner(client):
    owner = _auth(client, "ro@b.com")
    hid = client.post("/households", json={"name": "Home"}, headers=owner).json()["id"]
    r = client.patch(f"/households/{hid}", json={"name": "Casa"}, headers=owner)
    assert r.status_code == 200 and r.json()["name"] == "Casa"

def test_delete_household(client):
    owner = _auth(client, "rd@b.com")
    hid = client.post("/households", json={"name": "Home"}, headers=owner).json()["id"]
    assert client.delete(f"/households/{hid}", headers=owner).status_code == 204
    assert client.get("/households", headers=owner).json() == []

def test_owner_cannot_be_removed(client):
    owner = _auth(client, "rx@b.com")
    hid = client.post("/households", json={"name": "Home"}, headers=owner).json()["id"]
    uid = client.get("/auth/me", headers=owner).json()["id"]
    r = client.delete(f"/households/{hid}/members/{uid}", headers=owner)
    assert r.status_code == 400


def _add_member(db_session, client, household_id, email):
    """Register a user and directly insert a 'member' Membership; return their id + auth headers."""
    headers = _auth(client, email)
    uid = client.get("/auth/me", headers=headers).json()["id"]
    db_session.add(Membership(household_id=household_id, user_id=uid, role="member"))
    db_session.commit()
    return uid, headers

def test_non_member_forbidden_on_reads_and_mutations(client):
    owner = _auth(client, "secowner@b.com")
    hid = client.post("/households", json={"name": "Home"}, headers=owner).json()["id"]
    stranger = _auth(client, "stranger@b.com")
    assert client.get(f"/households/{hid}", headers=stranger).status_code == 403
    assert client.get(f"/households/{hid}/members", headers=stranger).status_code == 403
    assert client.patch(f"/households/{hid}", json={"name": "X"}, headers=stranger).status_code == 403
    assert client.delete(f"/households/{hid}", headers=stranger).status_code == 403

def test_member_cannot_mutate_household(client, db_session):
    owner = _auth(client, "mowner@b.com")
    hid = client.post("/households", json={"name": "Home"}, headers=owner).json()["id"]
    _, member = _add_member(db_session, client, hid, "plainmember@b.com")
    # member CAN read
    assert client.get(f"/households/{hid}", headers=member).status_code == 200
    # member CANNOT rename / delete / remove others
    assert client.patch(f"/households/{hid}", json={"name": "X"}, headers=member).status_code == 403
    assert client.delete(f"/households/{hid}", headers=member).status_code == 403
    owner_uid = client.get("/auth/me", headers=owner).json()["id"]
    assert client.delete(f"/households/{hid}/members/{owner_uid}", headers=member).status_code == 403

def test_owner_can_remove_real_member(client, db_session):
    owner = _auth(client, "rmowner@b.com")
    hid = client.post("/households", json={"name": "Home"}, headers=owner).json()["id"]
    member_uid, _ = _add_member(db_session, client, hid, "removable@b.com")
    # owner removes the member -> 204
    assert client.delete(f"/households/{hid}/members/{member_uid}", headers=owner).status_code == 204
    members = client.get(f"/households/{hid}/members", headers=owner).json()
    assert all(m["user_id"] != member_uid for m in members)
