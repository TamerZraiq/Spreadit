import pytest

#Dummy user payload for testing
def user_payload(id = 1, name = "Bob", email = "Bob@atu.ie", username = "LilBob", pw = "bob123", cid = 1,  year = 1, uid = "g00425076"):
    return {"id": id, "user_id": uid, "name": name, "email": email, "username": username, "password": pw, "course_id": cid, "year": year}

#Dummy user-signup payload for testing
def user_signup_payload(name = "Bob", email = "Bob@atu.ie", username = "LilBob", pw = "bob123", cid = 1,  year = 1, uid = "g00425076"):
    return {"user_id": uid, "name": name, "email": email, "username": username, "password": pw, "course_id": cid, "year": year}

#Test for the /sign-up endpoint
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
    client.post("/sign-up", json=user_signup_payload(uid = "g00425076")) 
    r = client.post("/sign-up", json=user_signup_payload(uid = "g00425076")) 
    assert r.status_code == 409 
    assert "user id already exists" in r.json()["detail"].lower() 

    #This tests when duplicate email occurs when signing up
def test_duplicate_email_conflict(client): 
    client.post("/sign-up", json=user_signup_payload(email = "Bob@atu.ie")) 
    r = client.post("/sign-up", json=user_signup_payload(uid = "g00425077", email = "Bob@atu.ie")) 
    assert r.status_code == 409 
    assert "email already exists" in r.json()["detail"].lower() 

    #This tests when duplicate username occurs when signing up
def test_duplicate_username_conflict(client): 
    client.post("/sign-up", json=user_signup_payload(username = "LilBob")) 
    r = client.post("/sign-up", json=user_signup_payload(uid = "g00425077", email = "Bobi@atu.ie", username = "LilBob"))
    assert r.status_code == 409 
    assert "username already exists" in r.json()["detail"].lower() 


