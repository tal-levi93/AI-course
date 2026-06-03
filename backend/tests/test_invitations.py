from app.security import generate_invite_token, hash_token


def test_invite_token_is_random_and_hashable():
    t1 = generate_invite_token()
    t2 = generate_invite_token()
    assert t1 != t2 and len(t1) >= 20
    assert hash_token(t1) == hash_token(t1)
    assert hash_token(t1) != t1
