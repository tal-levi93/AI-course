from pydantic import BaseModel, EmailStr, ConfigDict


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    display_name: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
