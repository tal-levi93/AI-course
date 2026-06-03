from app.models.user import User
from app.models.household import Household
from app.models.shopping import ShoppingList, ListItem


def test_list_and_item_models(db_session):
    u = User(email="s@b.com", password_hash="x", display_name="S"); db_session.add(u); db_session.commit()
    h = Household(name="Home", owner_id=u.id); db_session.add(h); db_session.commit()
    sl = ShoppingList(household_id=h.id, name="Groceries", created_by=u.id); db_session.add(sl); db_session.commit()
    it = ListItem(list_id=sl.id, name="Milk", quantity="2", added_by=u.id); db_session.add(it); db_session.commit()
    assert it.id is not None and it.is_checked is False
