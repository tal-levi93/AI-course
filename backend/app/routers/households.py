from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_member, require_owner
from app.models.household import Household, Membership
from app.models.user import User
from app.schemas.household import HouseholdCreate, HouseholdUpdate, HouseholdOut, MemberOut

router = APIRouter(tags=["households"])


@router.post("/households", response_model=HouseholdOut, status_code=201)
def create_household(payload: HouseholdCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    h = Household(name=payload.name, owner_id=user.id)
    db.add(h); db.flush()
    db.add(Membership(household_id=h.id, user_id=user.id, role="owner"))
    db.commit(); db.refresh(h)
    return h


@router.get("/households", response_model=list[HouseholdOut])
def my_households(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (
        db.query(Household)
        .join(Membership, Membership.household_id == Household.id)
        .filter(Membership.user_id == user.id)
        .all()
    )
    return rows


@router.get("/households/{household_id}/members", response_model=list[MemberOut])
def list_members(household_id: int, db: Session = Depends(get_db), _: Membership = Depends(require_member)):
    rows = (
        db.query(Membership.role, User.id, User.email, User.display_name)
        .join(User, User.id == Membership.user_id)
        .filter(Membership.household_id == household_id)
        .all()
    )
    return [MemberOut(user_id=r.id, email=r.email, display_name=r.display_name, role=r.role) for r in rows]
