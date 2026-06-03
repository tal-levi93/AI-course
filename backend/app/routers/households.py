from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_member, require_owner
from app.models.household import Household, Membership
from app.models.invitation import Invitation
from app.models.shopping import ShoppingList, ListItem
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


@router.get("/households/{household_id}", response_model=HouseholdOut)
def get_household(household_id: int, db: Session = Depends(get_db), _: Membership = Depends(require_member)):
    h = db.get(Household, household_id)
    if h is None:
        raise HTTPException(status_code=404, detail="Not found")
    return h


@router.patch("/households/{household_id}", response_model=HouseholdOut)
def rename_household(household_id: int, payload: HouseholdUpdate, db: Session = Depends(get_db), _: Membership = Depends(require_owner)):
    h = db.get(Household, household_id)
    if h is None:
        raise HTTPException(status_code=404, detail="Not found")
    h.name = payload.name
    db.commit(); db.refresh(h)
    return h


@router.delete("/households/{household_id}", status_code=204)
def delete_household(household_id: int, db: Session = Depends(get_db), _: Membership = Depends(require_owner)):
    list_ids = [row[0] for row in db.query(ShoppingList.id).filter(ShoppingList.household_id == household_id).all()]
    if list_ids:
        db.query(ListItem).filter(ListItem.list_id.in_(list_ids)).delete(synchronize_session=False)
    db.query(ShoppingList).filter(ShoppingList.household_id == household_id).delete(synchronize_session=False)
    db.query(Invitation).filter(Invitation.household_id == household_id).delete(synchronize_session=False)
    db.query(Membership).filter(Membership.household_id == household_id).delete(synchronize_session=False)
    h = db.get(Household, household_id)
    if h:
        db.delete(h)
    db.commit()


@router.delete("/households/{household_id}/members/{user_id}", status_code=204)
def remove_member(household_id: int, user_id: int, db: Session = Depends(get_db), _: Membership = Depends(require_owner)):
    h = db.get(Household, household_id)
    if h and h.owner_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot remove the owner")
    m = db.query(Membership).filter(Membership.household_id == household_id, Membership.user_id == user_id).first()
    if m is None:
        raise HTTPException(status_code=404, detail="Member not found")
    db.delete(m); db.commit()
