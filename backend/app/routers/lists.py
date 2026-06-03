from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_member, get_current_user
from app.models.household import Membership
from app.models.shopping import ShoppingList
from app.models.user import User
from app.schemas.shopping import ListCreate, ListOut

router = APIRouter(tags=["lists"])


@router.post("/households/{household_id}/lists", response_model=ListOut, status_code=201)
def create_list(household_id: int, payload: ListCreate, db: Session = Depends(get_db),
                _: Membership = Depends(require_member), user: User = Depends(get_current_user)):
    sl = ShoppingList(household_id=household_id, name=payload.name, created_by=user.id)
    db.add(sl); db.commit(); db.refresh(sl)
    return sl


@router.get("/households/{household_id}/lists", response_model=list[ListOut])
def list_lists(household_id: int, db: Session = Depends(get_db), _: Membership = Depends(require_member)):
    return db.query(ShoppingList).filter(ShoppingList.household_id == household_id).all()


@router.delete("/lists/{list_id}", status_code=204)
def delete_list(list_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    sl = db.get(ShoppingList, list_id)
    if sl is None:
        raise HTTPException(status_code=404, detail="List not found")
    m = db.query(Membership).filter(Membership.household_id == sl.household_id, Membership.user_id == user.id).first()
    if m is None:
        raise HTTPException(status_code=403, detail="Not a member")
    db.delete(sl); db.commit()
