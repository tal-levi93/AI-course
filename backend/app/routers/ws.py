from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.deps import get_membership
from app.models.user import User
from app.realtime import manager
from app.security import decode_token

router = APIRouter()


def _override_get_db():
    """Return the get_db dependency override (used in tests), if any."""
    from app.main import app

    return app.dependency_overrides.get(get_db)


def _open_db() -> Session:
    """Resolve a DB session, honoring any get_db dependency override (used in tests)."""
    override = _override_get_db()
    if override is not None:
        result = override()
        if hasattr(result, "__next__"):
            return next(result)
        return result
    return SessionLocal()


@router.websocket("/ws/households/{household_id}")
async def household_ws(websocket: WebSocket, household_id: int, token: str = Query(...)):
    subject = decode_token(token)
    if subject is None:
        await websocket.close(code=4401)
        return
    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        await websocket.close(code=4401)
        return
    db = _open_db()
    try:
        user = db.get(User, user_id)
        if user is None or get_membership(household_id, db, user) is None:
            await websocket.close(code=4403)
            return
    finally:
        # Don't close a session owned by the test override; only close our own.
        if _override_get_db() is None:
            db.close()
    await websocket.accept()
    manager.add(household_id, websocket)
    try:
        while True:
            await websocket.receive_text()  # keep-alive; ignore client messages
    except WebSocketDisconnect:
        manager.remove(household_id, websocket)
