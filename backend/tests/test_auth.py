from app.models.user import User


def test_user_model_fields(db_session):
    u = User(email="a@b.com", password_hash="x", display_name="A")
    db_session.add(u)
    db_session.commit()
    assert u.id is not None
    assert u.created_at is not None
