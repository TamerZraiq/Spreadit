import pytest 
from fastapi.testclient import TestClient 
from sqlalchemy import create_engine, event 
from sqlalchemy.orm import sessionmaker 
 
from app.main import app, get_db 
from app.models import Base, UserDB
from sqlalchemy.pool import StaticPool 
 
TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool) 
TestingSessionLocal = sessionmaker(bind=engine, expire_on_commit=False) 
 

@event.listens_for(engine, "connect") 
def _fk_on(dbapi_conn, _): 
    dbapi_conn.execute("PRAGMA foreign_keys=ON") 

@pytest.fixture(autouse=True) 
def _schema(): 
    Base.metadata.create_all(bind=engine) 
    yield 
    Base.metadata.drop_all(bind=engine) 
 
@pytest.fixture 
def client(): 
    def override_get_db(): 
        db = TestingSessionLocal() 
        try: 
            yield db 
        finally: 
            db.close() 
    app.dependency_overrides[get_db] = override_get_db 
    with TestClient(app) as c: 
        # hand the client to the test 
        yield c 
    app.dependency_overrides.clear() 

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

def user_update_payload(name = "Alan", email = "Alan@atu.ie", username = "LilAlan", pw = "Alan123", cid = 1,  year = 1, uid = "g00425077"):
    return {"user_id": uid, "name": name, "email": email, "username": username, "password": pw, "course_id": cid, "year": year}


##############################################################################################################################################

#This tests signup successful
def test_signup_ok(client): 
    r = client.post("/api/sign-up", json=user_signup_payload()) 
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
    client.post("/api/sign-up", json=user_signup_payload()) 
    r = client.post("/api/sign-up", json=second_user_payload(uid = "g00425076")) 
    assert r.status_code == 409 
    assert "student id already exists" in r.json()["detail"].lower() 

#This tests when duplicate email occurs when signing up
def test_duplicate_email_conflict(client): 
    client.post("/api/sign-up", json=user_signup_payload()) 
    r = client.post("/api/sign-up", json=second_user_payload(email = "Bob@atu.ie")) 
    assert r.status_code == 409 
    assert "email already exists" in r.json()["detail"].lower() 

#This tests when duplicate username occurs when signing up
def test_duplicate_username_conflict(client): 
    client.post("/api/sign-up", json=user_signup_payload()) 
    r = client.post("/api/sign-up", json=second_user_payload(username = "LilBob"))
    assert r.status_code == 409 
    assert "username already exists" in r.json()["detail"].lower() 



#This tests login successful
def test_login_ok(client):
    client.post("/api/sign-up", json=user_signup_payload()) 
    r = client.post("/api/login", json=user_login_payload())
    assert r.status_code == 200 

#This tests when login with wrong password
def test_login_wrong_password(client):
    client.post("/api/sign-up", json=user_signup_payload())
    r = client.post("/api/login", json= user_login_payload(pw = "wrongpassword"))
    assert r.status_code == 401
    assert "invalid email or password" in r.json()["detail"].lower() 

#This tests when login with wrong email
def test_login_wrong_email(client):
    client.post("/api/sign-up", json=user_signup_payload())
    r = client.post("/api/login", json= user_login_payload(email = "wrongemail@atu.ie"))
    assert r.status_code == 401
    assert "invalid email or password" in r.json()["detail"].lower() 

#This tests listing all the existing user
def test_list_user_ok(client):
    client.post("/api/sign-up", json=user_signup_payload())
    r = client.get("/api/all-users")
    assert r.status_code == 200
    assert r.json() == [user_payload()]

#This tests getting user by their user_id
def test_get_user_by_id_ok(client):
    client.post("/api/sign-up", json=user_signup_payload())
    r = client.get("/api/user-by-userid/g00425076")
    assert r.status_code == 200
    assert r.json() == user_payload()

#This tests when trying to get user by using the wrong user_id
def test_get_user_by_id_not_found(client):
    client.post("/api/sign-up", json=user_signup_payload())
    #Wrong student ID here (should be g00425076)
    r = client.get("/api/user-by-userid/g00425075")
    assert r.status_code == 404
    assert "user not found" in r.json()["detail"].lower()

#This tests updating a user using their user-id
def test_update_user_ok(client):
    client.post("/api/sign-up", json=user_signup_payload())
    r = client.put("/api/update-user-by-userid/g00425076", json=user_update_payload())
    assert r.status_code == 200
    assert "updated user successful" in r.json()["message"].lower() 

#This tests when trying to update a user that doesn't exist
def test_update_user_not_found(client):
    client.post("/api/sign-up", json=user_signup_payload())
    r = client.put("/api/update-user-by-userid/g00425075", json=user_update_payload())
    assert r.status_code == 404
    assert "id not found" in r.json()["detail"].lower() 

#this tests deleting a user
def test_delete_user_ok(client):
    client.post("/api/sign-up", json=user_signup_payload())
    r = client.delete("/api/delete-user-by-userid/g00425076")
    assert r.status_code == 200
    assert "deleted user" in r.json()["message"].lower() 

#This tests when trying to delete a user that doesn't exist
def test_delete_user_not_found(client):
    client.post("/api/sign-up", json=user_signup_payload())
    r = client.delete("/api/delete-user-by-userid/g00425075")
    assert r.status_code == 404
    assert "user_id not found" in r.json()["detail"].lower() 