from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ListCreate(BaseModel):
    name: str


class ListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    household_id: int
    name: str


class ItemCreate(BaseModel):
    name: str
    quantity: str | None = None
    category: str | None = None
    note: str | None = None


class ItemUpdate(BaseModel):
    name: str | None = None
    quantity: str | None = None
    category: str | None = None
    note: str | None = None
    is_checked: bool | None = None


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    list_id: int
    name: str
    quantity: str | None
    category: str | None
    note: str | None
    is_checked: bool
    added_by: int
    checked_by: int | None
