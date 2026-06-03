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
