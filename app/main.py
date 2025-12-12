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
import httpx
import os
import aio_pika
import json
import asyncio

COURSE_SERVICE_URL = os.getenv("COURSE_SERVICE_URL", "http://localhost:8000")
POST_SERVICE_URL = os.getenv("POST_SERVICE_URL", "http://localhost:8000")
RABBIT_URL = os.getenv("RABBIT_URL")

async def publish_event(routing_key: str, data: dict):
    if not RABBIT_URL:
        return
        
    try:
        connection = await aio_pika.connect_robust(RABBIT_URL)
        async with connection:
            channel = await connection.channel()
            exchange = await channel.declare_exchange("events_topic", aio_pika.ExchangeType.TOPIC)
            
            message = aio_pika.Message(
                body=json.dumps(data).encode(),
                content_type="application/json"
            )
            await exchange.publish(message, routing_key=routing_key)
    except Exception as e:
        print(f"Failed to publish event {routing_key}: {e}")

    except Exception as e:
        print(f"Failed to publish event {routing_key}: {e}")

async def process_course_deleted(data: dict):
    course_id = data.get("course_id")
    if not course_id:
        return

    print(f"Processing course deletion for course_id: {course_id}")
    db = SessionLocal()
    try:
        # UserDB has course_id as Integer, but RabbitMQ payload might be string/int.
        # Assuming we want to reset it to 0 or some default if the course is gone.
        # Note: If course_id is "1", ensure we check types.
        
        # We try to cast to int, if fails, might not match anyway.
        try:
            cid_int = int(course_id)
            users = db.query(UserDB).filter(UserDB.course_id == cid_int).all()
            for user in users:
                user.course_id = 0 # 0 represents "No Course" or "Unassigned"
            
            db.commit()
            print(f"Reset course_id for {len(users)} users who were in course {course_id}")
        except ValueError:
            print(f"Invalid course_id format received: {course_id}")
            
    except Exception as e:
        print(f"Error processing course deletion in User Service: {e}")
        db.rollback()
    finally:
        db.close()

async def consume_events():
    if not RABBIT_URL:
        print("RABBIT_URL not set, skipping consumer")
        return

    while True:
        try:
            connection = await aio_pika.connect_robust(RABBIT_URL)
            async with connection:
                channel = await connection.channel()
                
                await channel.declare_exchange("events_topic", aio_pika.ExchangeType.TOPIC)
                queue = await channel.declare_queue("user_service_queue", durable=True)
                
                # Bind to course.deleted
                await queue.bind("events_topic", routing_key="course.deleted")
                
                print("User Service Consumer Started")
                
                async with queue.iterator() as iterator:
                    async for message in iterator:
                        async with message.process():
                            data = json.loads(message.body)
                            if message.routing_key == "course.deleted":
                                await process_course_deleted(data)

        except asyncio.CancelledError:
            print("Consumer cancelled")
            break
        except Exception as e:
            print(f"Consumer connection lost: {e}, retrying in 5s...")
            await asyncio.sleep(5)

app = FastAPI()
users: list[User] = []

# Replaces @app.on_event("startup")
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    task = asyncio.create_task(consume_events())
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
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.email == request.email, UserDB.password == request.password).first() #query the db for any row or entry that has a matching email and password to the request one
    if user:
        await publish_event("user.login", {"user_id": user.user_id})
        return {
            "message": "Login successful", 
            "user_id": user.user_id,
            "is_admin": user.is_admin
        }
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Email or Password")

#update a user by user id, still requires error catching 
@app.put("/api/update-user-by-userid/{user_id}", status_code=status.HTTP_200_OK)
async def update_user(user_id: str, updated_user: UserUpdate, db: Session = Depends(get_db)):
    result = db.query(UserDB).filter(UserDB.user_id == user_id).update(updated_user.model_dump())
    db.commit()

    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="id not found")

    await publish_event("user.updated", {"user_id": user_id, "updates": updated_user.model_dump()})
    return {"message": "Updated User successful"}

#delete user by user id
@app.delete("/api/delete-user-by-userid/{user_id}", status_code=status.HTTP_200_OK)
async def delete_user(user_id: str, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_id not found")
    db.delete(user)
    db.commit()

    await publish_event("user.deleted", {"user_id": user_id})
    return {"message": "Deleted User"}


# ------------------------- Our Code -------------------------
#signup
@app.post("/api/sign-up", response_model=User, status_code=status.HTTP_201_CREATED)
async def add_user(payload: UserSignUp, db: Session = Depends(get_db)):
    # Check for existing email and username
    existing_email = db.query(UserDB).filter(UserDB.email == payload.email).first()
    if existing_email:
        raise HTTPException(status_code=409, detail="Email already exists")
    existing_username = db.query(UserDB).filter(UserDB.username == payload.username).first()
    if existing_username:
        raise HTTPException(status_code=409, detail="Username already exists")
    
    # Auto-generate user_id from email (use part before @)
    user_id_base = payload.email.split('@')[0]
    # Make it unique by appending a number if needed
    user_id = user_id_base
    counter = 1
    while db.query(UserDB).filter(UserDB.user_id == user_id).first():
        user_id = f"{user_id_base}{counter}"
        counter += 1
    
    # Check if password is the admin password
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "ADMIN2025")
    is_admin = payload.password == ADMIN_PASSWORD
    
    # Create user data with auto-generated fields
    user_data = payload.model_dump()
    user_data["user_id"] = user_id
    user_data["course_id"] = 0  # Default to 0 (no course assigned)
    user_data["is_admin"] = is_admin
    
    user = UserDB(**user_data)
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
        await publish_event("user.created", {"user_id": user.user_id, "username": user.username, "is_admin": is_admin})
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="User already exists")
    return user
    
@app.get("/health") #health checkup function 
def health():
    return {"status" : "ok"}

@app.get("/api/proxy/courses")
def proxy_courses():
    with httpx.Client() as client:
        response = client.get(f"{COURSE_SERVICE_URL}/api/get-all-courses")
    return response.json()

@app.get("/api/proxy/posts")
def proxy_posts():
    with httpx.Client() as client:
        response = client.get(f"{POST_SERVICE_URL}/api/get-all-posts")
    return response.json()