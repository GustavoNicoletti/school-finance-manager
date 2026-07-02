from pydantic import BaseModel, EmailStr, Field

from app.schemas.user import UserRead


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
