import asyncio
from app.realtime import ConnectionManager


class FakeWS:
    def __init__(self):
        self.sent = []

    async def send_json(self, data):
        self.sent.append(data)


def test_broadcast_only_to_household():
    mgr = ConnectionManager()
    a, b, c = FakeWS(), FakeWS(), FakeWS()
    mgr.add(1, a)
    mgr.add(1, b)
    mgr.add(2, c)
    asyncio.run(mgr.broadcast(1, {"type": "item.added"}))
    assert a.sent and b.sent and not c.sent
    mgr.remove(1, a)
    asyncio.run(mgr.broadcast(1, {"type": "x"}))
    assert len(a.sent) == 1  # no new message after removal


def test_ws_receives_item_added(client):
    client.post("/auth/register", json={"email": "w@b.com", "password": "secret123", "display_name": "W"})
    token = client.post("/auth/login", json={"email": "w@b.com", "password": "secret123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    hid = client.post("/households", json={"name": "Home"}, headers=headers).json()["id"]
    lid = client.post(f"/households/{hid}/lists", json={"name": "G"}, headers=headers).json()["id"]
    with client.websocket_connect(f"/ws/households/{hid}?token={token}") as ws:
        client.post(f"/lists/{lid}/items", json={"name": "Eggs"}, headers=headers)
        msg = ws.receive_json()
        assert msg["type"] == "item.added" and msg["item"]["name"] == "Eggs"


def test_ws_rejects_invalid_token(client):
    from starlette.websockets import WebSocketDisconnect
    import pytest

    client.post("/auth/register", json={"email": "w2@b.com", "password": "secret123", "display_name": "W"})
    token = client.post("/auth/login", json={"email": "w2@b.com", "password": "secret123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    hid = client.post("/households", json={"name": "Home"}, headers=headers).json()["id"]
    # connect with a bogus token -> server should close before accepting; receiving raises
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws/households/{hid}?token=bogus") as ws:
            ws.receive_json()


def test_broadcast_survives_dead_socket():
    mgr = ConnectionManager()

    class DeadWS:
        async def send_json(self, data):
            raise RuntimeError("socket closed")

    good = FakeWS()
    dead = DeadWS()
    mgr.add(5, dead); mgr.add(5, good)
    asyncio.run(mgr.broadcast(5, {"type": "item.added"}))
    # the good socket still received the message despite the dead one raising
    assert good.sent == [{"type": "item.added"}]
