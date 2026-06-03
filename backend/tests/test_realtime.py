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
