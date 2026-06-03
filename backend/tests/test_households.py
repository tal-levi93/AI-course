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
