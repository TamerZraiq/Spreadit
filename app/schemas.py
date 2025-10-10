# app/schemas.py
from pydantic import BaseModel, EmailStr, constr
from typing import Literal

class User(BaseModel):
    id: int
    user_id: constr(pattern=r'^g\d{8}$')
    name: str
    email: EmailStr
    username: str
    password: str
    course_id: int
    year: list[Literal[1, 2, 3, 4]] #Only allows 1, 2, 3, or 4