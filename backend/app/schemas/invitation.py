from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr


class InviteCreate(BaseModel):
    email: EmailStr


class InviteCreatedOut(BaseModel):
    id: int
    email: EmailStr
    token: str          # raw token, returned ONCE
    accept_url: str
    expires_at: datetime


class InviteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    status: str
    expires_at: datetime


class AcceptRequest(BaseModel):
    token: str


class AcceptResult(BaseModel):
    household_id: int
    role: str = "member"
