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


def test_register_creates_user(client):
    r = client.post("/auth/register", json={
        "email": "new@b.com", "password": "secret123", "display_name": "New"
    })
    assert r.status_code == 201
    data = r.json()
    assert data["email"] == "new@b.com"
    assert "password" not in data and "password_hash" not in data


def test_register_duplicate_email(client):
    payload = {"email": "dup@b.com", "password": "secret123", "display_name": "D"}
    client.post("/auth/register", json=payload)
    r = client.post("/auth/register", json=payload)
    assert r.status_code == 409


def test_login_success(client):
    client.post("/auth/register", json={"email": "l@b.com", "password": "secret123", "display_name": "L"})
    r = client.post("/auth/login", json={"email": "l@b.com", "password": "secret123"})
    assert r.status_code == 200
    assert r.json()["access_token"]


def test_login_wrong_password(client):
    client.post("/auth/register", json={"email": "l2@b.com", "password": "secret123", "display_name": "L"})
    r = client.post("/auth/login", json={"email": "l2@b.com", "password": "nope"})
    assert r.status_code == 401
