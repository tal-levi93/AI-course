from app.models.user import User
from app.models.household import Household
from app.models.shopping import ShoppingList, ListItem


def test_list_and_item_models(db_session):
    u = User(email="s@b.com", password_hash="x", display_name="S"); db_session.add(u); db_session.commit()
    h = Household(name="Home", owner_id=u.id); db_session.add(h); db_session.commit()
    sl = ShoppingList(household_id=h.id, name="Groceries", created_by=u.id); db_session.add(sl); db_session.commit()
    it = ListItem(list_id=sl.id, name="Milk", quantity="2", added_by=u.id); db_session.add(it); db_session.commit()
    assert it.id is not None and it.is_checked is False


def _auth(client, email):
    client.post("/auth/register", json={"email": email, "password": "secret123", "display_name": email[:1]})
    t = client.post("/auth/login", json={"email": email, "password": "secret123"}).json()["access_token"]
    return {"Authorization": f"Bearer {t}"}


def test_create_and_list_lists(client):
    h = _auth(client, "ll@b.com")
    hid = client.post("/households", json={"name": "Home"}, headers=h).json()["id"]
    r = client.post(f"/households/{hid}/lists", json={"name": "Groceries"}, headers=h)
    assert r.status_code == 201
    lists = client.get(f"/households/{hid}/lists", headers=h).json()
    assert len(lists) == 1 and lists[0]["name"] == "Groceries"


def test_non_member_cannot_create_list(client):
    owner = _auth(client, "lo@b.com")
    hid = client.post("/households", json={"name": "Home"}, headers=owner).json()["id"]
    stranger = _auth(client, "ls@b.com")
    r = client.post(f"/households/{hid}/lists", json={"name": "X"}, headers=stranger)
    assert r.status_code == 403


def _list(client, headers):
    hid = client.post("/households", json={"name": "Home"}, headers=headers).json()["id"]
    lid = client.post(f"/households/{hid}/lists", json={"name": "G"}, headers=headers).json()["id"]
    return hid, lid


def test_add_check_delete_item(client):
    h = _auth(client, "it@b.com")
    _, lid = _list(client, h)
    iid = client.post(f"/lists/{lid}/items", json={"name": "Milk", "quantity": "2"}, headers=h).json()["id"]
    items = client.get(f"/lists/{lid}/items", headers=h).json()
    assert len(items) == 1 and items[0]["name"] == "Milk"
    upd = client.patch(f"/items/{iid}", json={"is_checked": True}, headers=h).json()
    assert upd["is_checked"] is True and upd["checked_by"] is not None
    assert client.delete(f"/items/{iid}", headers=h).status_code == 204
    assert client.get(f"/lists/{lid}/items", headers=h).json() == []
