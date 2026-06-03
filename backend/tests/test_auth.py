from app.models.user import User
from app.security import hash_password, verify_password, create_access_token, decode_token


def test_user_model_fields(db_session):
    u = User(email="a@b.com", password_hash="x", display_name="A")
    db_session.add(u)
    db_session.commit()
    assert u.id is not None
    assert u.created_at is not None


def test_password_hash_roundtrip():
    h = hash_password("secret")
    assert h != "secret"
    assert verify_password("secret", h)
    assert not verify_password("wrong", h)


def test_jwt_roundtrip():
    token = create_access_token(subject="42")
    assert decode_token(token) == "42"
