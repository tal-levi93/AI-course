from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.household import Membership
from app.models.shopping import ShoppingList, ListItem
from app.models.user import User
from app.schemas.shopping import ItemCreate, ItemUpdate, ItemOut

router = APIRouter(tags=["items"])


def _list_or_403(list_id: int, db: Session, user: User) -> ShoppingList:
    sl = db.get(ShoppingList, list_id)
    if sl is None:
        raise HTTPException(status_code=404, detail="List not found")
    m = db.query(Membership).filter(Membership.household_id == sl.household_id, Membership.user_id == user.id).first()
    if m is None:
        raise HTTPException(status_code=403, detail="Not a member")
    return sl


def _item_or_403(item_id: int, db: Session, user: User) -> ListItem:
    it = db.get(ListItem, item_id)
    if it is None:
        raise HTTPException(status_code=404, detail="Item not found")
    _list_or_403(it.list_id, db, user)
    return it


@router.post("/lists/{list_id}/items", response_model=ItemOut, status_code=201)
def add_item(list_id: int, payload: ItemCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _list_or_403(list_id, db, user)
    it = ListItem(list_id=list_id, added_by=user.id, **payload.model_dump())
    db.add(it); db.commit(); db.refresh(it)
    return it


@router.get("/lists/{list_id}/items", response_model=list[ItemOut])
def list_items(list_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _list_or_403(list_id, db, user)
    return db.query(ListItem).filter(ListItem.list_id == list_id).all()


@router.patch("/items/{item_id}", response_model=ItemOut)
def update_item(item_id: int, payload: ItemUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    it = _item_or_403(item_id, db, user)
    data = payload.model_dump(exclude_unset=True)
    if "is_checked" in data:
        it.checked_by = user.id if data["is_checked"] else None
    for k, v in data.items():
        setattr(it, k, v)
    db.commit(); db.refresh(it)
    return it


@router.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    it = _item_or_403(item_id, db, user)
    db.delete(it); db.commit()
