# app/schemas.py
from pydantic import BaseModel, EmailStr, constr, conint, ConfigDict
from typing import Literal, Optional

class User(BaseModel):
    id: int
    user_id: str
    name: str
    email: EmailStr
    username: str
    password: str
    course_id: int
    year: conint(ge=1, le=4)
    is_admin: bool = False
    enrolled_modules: list[int] = []

    model_config = ConfigDict(from_attributes=True)


class UserSignUp(BaseModel):
    name: str
    email: EmailStr
    username: str
    password: str
    year: conint(ge=1, le=4)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    user_id: str
    name: str
    email: EmailStr
    username: str
    password: str
    course_id: int
    year: conint(ge=1, le=4)
    is_admin: Optional[bool] = None