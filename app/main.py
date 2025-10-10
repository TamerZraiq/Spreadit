# app/main.py
from fastapi import FastAPI, HTTPException, status
from .schemas import User

app = FastAPI()
users: list[User] = []

@app.get("/api/users")
def get_users():
    return users

@app.get("/api/users/{user_id}")
def get_user(user_id: int):
    for u in users: # search for user by ID
        if u.user_id == user_id:
            return u
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found") #if not found return 404

@app.post("/api/users", status_code=status.HTTP_201_CREATED)
def add_user(user: User):
    if any(u.user_id == user.user_id for u in users): # to prevent duplicate user id's
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="user_id already exists")
    users.append(user) # add new user to the users list
    return user

@app.put("/api/users/{user_id}", status_code=status.HTTP_200_OK)
def update_user(user_id: int, updated_user: User):
    for i, u in enumerate(users): #find user by id and replace the updated user data
        if u.user_id == user_id:
            users[i] = updated_user
            return updated_user 
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_id already exists") #if not found return 404

@app.delete("/api/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int):
    for u in users: 
        if u.user_id == user_id: # find user by id and delete from list
            users.remove(u)
            return u 
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_id not found")
    
@app.get("/health") #health checkup function 
def health():
    return {"status" : "ok"}