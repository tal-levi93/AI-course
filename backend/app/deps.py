from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.security import decode_token

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    subject = decode_token(creds.credentials)
    if subject is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.get(User, int(subject))
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user
