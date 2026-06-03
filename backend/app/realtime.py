from collections import defaultdict


class ConnectionManager:
    def __init__(self):
        self._rooms: dict[int, set] = defaultdict(set)

    def add(self, household_id: int, ws):
        self._rooms[household_id].add(ws)

    def remove(self, household_id: int, ws):
        self._rooms[household_id].discard(ws)

    async def broadcast(self, household_id: int, message: dict):
        for ws in list(self._rooms.get(household_id, set())):
            await ws.send_json(message)


manager = ConnectionManager()
