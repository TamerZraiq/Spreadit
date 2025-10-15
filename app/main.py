# app/main.py
from fastapi import FastAPI, HTTPException, status
from pydantic import EmailStr
from .schemas import User, UserSignUp, LoginRequest

app = FastAPI()
users: list[User] = []


@app.get("/api/users")
def get_users():
    return users

@app.get("/api/users/{id}")
def get_user(id: int):
    for u in users: # search for user by ID
        if u.id == id:
            return u
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found") #if not found return 404

@app.post("/sign-up", status_code=status.HTTP_201_CREATED, response_model=User)
def sign_up(user: UserSignUp):
    if any(u.user_id == user.user_id for u in users):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User ID already exists")
    if any(u.email == user.email for u in users):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")
    if any(u.username == user.username for u in users):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")
    id_sign_up = max([u.id for u in users], default=0) + 1
    user_sign_up = User(id=id_sign_up, **user.model_dump())
    users.append(user_sign_up)
    return user_sign_up

@app.post("/login", status_code=status.HTTP_200_OK)
def login(request: LoginRequest):
    if any(u.email == request.email and u.password == request.password for u in users):
        return {"message": "Login successful"}
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Email or Password")


@app.put("/api/users/{id}", status_code=status.HTTP_200_OK)
def update_user(id: int, updated_user: User):
    for i, u in enumerate(users): #find user by id and replace the updated user data
        if u.id == id:
            users[i] = updated_user
            return updated_user 
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="id already exists") #if not found return 404

@app.delete("/api/users/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(id: int):
    for u in users: 
        if u.id == id: # find user by id and delete from list
            users.remove(u)
            return u 
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="id not found")
    
@app.get("/health") #health checkup function 
def health():
    return {"status" : "ok"}