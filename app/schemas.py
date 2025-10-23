# app/schemas.py
from pydantic import BaseModel, EmailStr, constr, conint, ConfigDict
from typing import Literal

class User(BaseModel):
    id: int
    user_id: constr(pattern=r'^g\d{8}$')
    name: str
    email: EmailStr
    username: str
    password: str
    course_id: int
    year: conint(ge=1, le=4)

    model_config = ConfigDict(from_attributes=True)


class UserSignUp(BaseModel):
    user_id: constr(pattern=r'^g\d{8}$')
    name: str
    email: EmailStr
    username: str
    password: str
    course_id: int
    year: conint(ge=1, le=4)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    user_id: constr(pattern=r'^g\d{8}$')
    name: str
    email: EmailStr
    username: str
    password: str
    course_id: int
    year: conint(ge=1, le=4)