# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status, Response, Body
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from app.database import engine, SessionLocal
from .models import Base, UserDB
from .schemas import User, UserSignUp, LoginRequest, UserUpdate

app = FastAPI()
users: list[User] = []

# Replaces @app.on_event("startup")
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(lifespan=lifespan)

# CORS (dev-friendly; tighten in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # specify domains in prod
    allow_methods=["*"],
    allow_headers=["*"],
)

#establish connection to db
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

#using db to get users
@app.get("/api/all-users", response_model=list[User])
def get_users(db: Session = Depends(get_db)):
    stmt = select(UserDB).order_by(UserDB.id)
    return list(db.execute(stmt).scalars())

#get user by user id from db
@app.get("/api/user-by-userid/{user_id}", response_model=User)
def get_user(user_id: str, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.user_id == user_id).first()
    if not user: 
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found") #if not found return 404
    return user

#login to user in db
@app.post("/api/login", status_code=status.HTTP_200_OK)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.email == request.email, UserDB.password == request.password).first() #query the db for any row or entry that has a matching email and password to the request one
    if user:
        return {"message": "Login successful"}
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Email or Password")

#update a user by user id, still requires error catching 
@app.put("/api/update-user-by-userid/{user_id}", status_code=status.HTTP_200_OK)
def update_user(user_id: str, updated_user: UserUpdate, db: Session = Depends(get_db)):
    result = db.query(UserDB).filter(UserDB.user_id == user_id).update(updated_user.model_dump())
    db.commit()

    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="id not found")

    return {"message": "Updated User successful"}

#delete user by user id
@app.delete("/api/delete-user-by-userid/{user_id}", status_code=status.HTTP_200_OK)
def delete_user(user_id: str, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.user_id == user_id).first()
    db.delete(user)
    db.commit()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_id not found")

    return {"message": "Deleted User"}


# ------------------------- Our Code -------------------------
#signup
@app.post("/api/sign-up", response_model=User, status_code=status.HTTP_201_CREATED)
def add_user(payload: UserSignUp, db: Session = Depends(get_db)):
    existing_user_id = db.query(UserDB).filter(UserDB.user_id == payload.user_id).first()
    if existing_user_id:
        raise HTTPException(status_code=409, detail="Student ID already exists")
    existing_email = db.query(UserDB).filter(UserDB.email == payload.email).first()
    if existing_email:
        raise HTTPException(status_code=409, detail="Email already exists")
    existing_username = db.query(UserDB).filter(UserDB.username == payload.username).first()
    if existing_username:
        raise HTTPException(status_code=409, detail="Username already exists")
    user = UserDB(**payload.model_dump())
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="User already exists")
    return user
    
@app.get("/health") #health checkup function 
def health():
    return {"status" : "ok"}