from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    village: str | None = None
    phone: str | None = None
    active: bool

    class Config:
        from_attributes = True


class UserCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)
    role: str
    village: str | None = None
    phone: str | None = None


class UserStatusUpdate(BaseModel):
    active: bool
