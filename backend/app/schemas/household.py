from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr


class HouseholdCreate(BaseModel):
    name: str


class HouseholdUpdate(BaseModel):
    name: str


class HouseholdOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    owner_id: int
    created_at: datetime


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: int
    email: EmailStr
    display_name: str
    role: str
