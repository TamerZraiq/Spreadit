import pytest

#Payload for testing
def user_payload(id = 1, name = "Bob", email = "Bob@atu.ie", username = "LilBob", pw = "bob123", cid = 1,  year = 1, uid = "g00425076"):
    return {"id": id, "user_id": uid, "name": name, "email": email, "username": username, "password": pw, "course_id": cid, "year": year}

#Payload for user signup testing
def user_signup_payload(name = "Bob", email = "Bob@atu.ie", username = "LilBob", pw = "bob123", cid = 1,  year = 1, uid = "g00425076"):
    return {"user_id": uid, "name": name, "email": email, "username": username, "password": pw, "course_id": cid, "year": year}

#Payload for a second user (used for testing duplicate credentials when signing up)
def second_user_payload(name = "Alan", email = "Alan@atu.ie", username = "LilAlan", pw = "Alan123", cid = 1,  year = 1, uid = "g00425077"):
    return {"user_id": uid, "name": name, "email": email, "username": username, "password": pw, "course_id": cid, "year": year}

#Dummy payload for user login testing
def user_login_payload(email = "Bob@atu.ie", pw = "bob123"):
    return {"email": email, "password": pw}


##############################################################################################################################################

#This tests signup successful
def test_signup_ok(client): 
    r = client.post("/sign-up", json=user_signup_payload()) 
    assert r.status_code == 201 
    data = r.json() 
    assert data["id"] == 1 
    assert data["user_id"] == "g00425076"
    assert data["name"] == "Bob" 
    assert data["email"] == "Bob@atu.ie" 
    assert data["username"] == "LilBob" 
    assert data["password"] == "bob123" 
    assert data["course_id"] == 1
    assert data["year"] == 1
     
#This tests when duplicate user id occurs when signing up
def test_duplicate_user_id_conflict(client): 
    client.post("/sign-up", json=user_signup_payload()) 
    r = client.post("/sign-up", json=second_user_payload(uid = "g00425076")) 
    assert r.status_code == 409 
    assert "user id already exists" in r.json()["detail"].lower() 

#This tests when duplicate email occurs when signing up
def test_duplicate_email_conflict(client): 
    client.post("/sign-up", json=user_signup_payload()) 
    r = client.post("/sign-up", json=second_user_payload(email = "Bob@atu.ie")) 
    assert r.status_code == 409 
    assert "email already exists" in r.json()["detail"].lower() 

#This tests when duplicate username occurs when signing up
def test_duplicate_username_conflict(client): 
    client.post("/sign-up", json=user_signup_payload()) 
    r = client.post("/sign-up", json=second_user_payload(username = "LilBob"))
    assert r.status_code == 409 
    assert "username already exists" in r.json()["detail"].lower() 

#This tests login successful
def test_login_ok(client):
    client.post("/sign-up", json=user_signup_payload()) 
    r = client.post("/login", json=user_login_payload())
    assert r.status_code == 200 

#This tests when login with wrong password
def test_login_wrong_password(client):
    client.post("/sign-up", json=user_signup_payload())
    r = client.post("/login", json= user_login_payload(pw = "wrongpassword"))
    assert r.status_code == 401
    assert "invalid email or password" in r.json()["detail"].lower() 

#This tests when login with wrong email
def test_login_wrong_email(client):
    client.post("/sign-up", json=user_signup_payload())
    r = client.post("/login", json= user_login_payload(email = "wrongemail@atu.ie"))
    assert r.status_code == 401
    assert "invalid email or password" in r.json()["detail"].lower() 