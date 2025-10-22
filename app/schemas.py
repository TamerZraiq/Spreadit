# app/schemas.py
from pydantic import BaseModel, EmailStr, constr, conint
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