from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_membership
from app.models.user import User
from app.security import decode_token
from app.realtime import manager

router = APIRouter()


@router.websocket("/ws/households/{household_id}")
async def household_ws(
    websocket: WebSocket,
    household_id: int,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    subject = decode_token(token)
    if subject is None:
        await websocket.close(code=4401)
        return
    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        await websocket.close(code=4401)
        return
    user = db.get(User, user_id)
    if user is None or get_membership(household_id, db, user) is None:
        await websocket.close(code=4403)
        return
    await websocket.accept()
    manager.add(household_id, websocket)
    try:
        while True:
            await websocket.receive_text()  # keep-alive; ignore client messages
    except WebSocketDisconnect:
        manager.remove(household_id, websocket)
