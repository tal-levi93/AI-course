from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.household import Membership
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


def get_membership(household_id: int, db: Session, user: User) -> Membership | None:
    return (
        db.query(Membership)
        .filter(Membership.household_id == household_id, Membership.user_id == user.id)
        .first()
    )


def require_member(household_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Membership:
    m = get_membership(household_id, db, user)
    if m is None:
        raise HTTPException(status_code=403, detail="Not a member of this household")
    return m


def require_owner(household_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Membership:
    m = get_membership(household_id, db, user)
    if m is None or m.role != "owner":
        raise HTTPException(status_code=403, detail="Owner permission required")
    return m
