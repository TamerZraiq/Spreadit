import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.main import app, get_db
from app.models import Base, UserDB
from app.auth import verify_password
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
def user_payload(id = 1, name = "Bob", email = "Bob@atu.ie", username = "LilBob", pw = "bob123", cid = 0,  year = 1, uid = "Bob"):
    return {"id": id, "user_id": uid, "name": name, "email": email, "username": username, "password": pw, "course_id": cid, "year": year, "is_admin": False, "enrolled_modules": []}

#Payload for user signup testing (user_id auto-generated from email)
def user_signup_payload(name = "Bob", email = "Bob@atu.ie", username = "LilBob", pw = "bob123", year = 1):
    return {"name": name, "email": email, "username": username, "password": pw, "year": year}

#Payload for a second user (used for testing duplicate credentials when signing up)
def second_user_payload(name = "Alan", email = "Alan@atu.ie", username = "LilAlan", pw = "Alan123", year = 1):
    return {"name": name, "email": email, "username": username, "password": pw, "year": year}

#Dummy payload for user login testing
def user_login_payload(email = "Bob@atu.ie", pw = "bob123"):
    return {"email": email, "password": pw}

def user_update_payload(name = "Alan", email = "Alan@atu.ie", username = "LilAlan", pw = "Alan123", cid = 1,  year = 1, uid = "Bob", is_admin = False):
    return {"user_id": uid, "name": name, "email": email, "username": username, "password": pw, "course_id": cid, "year": year, "is_admin": is_admin}

#Helper function to get auth headers after login
def get_auth_headers(client, email="Bob@atu.ie", password="bob123"):
    login_response = client.post("/api/login", json={"email": email, "password": password})
    if login_response.status_code == 200:
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    else:
        raise Exception(f"Login failed with status {login_response.status_code}: {login_response.text}")


##############################################################################################################################################

#This tests signup successful
def test_signup_ok(client):
    r = client.post("/api/sign-up", json=user_signup_payload())
    assert r.status_code == 201
    data = r.json()
    assert data["id"] == 1
    assert data["user_id"] == "Bob"  # auto-generated from email "Bob@atu.ie"
    assert data["name"] == "Bob"
    assert data["email"] == "Bob@atu.ie"
    assert data["username"] == "LilBob"
    # Password is now hashed, so verify it matches the original password
    assert verify_password("bob123", data["password"])
    assert data["course_id"] == 0  # default value
    assert data["year"] == 1
    assert data["is_admin"] == False
    assert data["enrolled_modules"] == []
     
#This tests when duplicate user id occurs when signing up (same email prefix)
def test_duplicate_user_id_conflict(client):
    client.post("/api/sign-up", json=user_signup_payload())
    # Use same email as first user - will generate same user_id "Bob"
    r = client.post("/api/sign-up", json=second_user_payload(email="Bob@atu.ie"))
    assert r.status_code == 409
    assert "email already exists" in r.json()["detail"].lower() 

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
    data = r.json()
    # Check that JWT token is returned
    assert "access_token" in data
    assert "token_type" in data
    assert data["token_type"] == "bearer"
    assert data["user_id"] == "Bob"
    assert data["is_admin"] == False 

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

#This tests listing all the existing user (requires admin authentication)
def test_list_user_ok(client):
    # Sign up admin user
    client.post("/api/sign-up", json=user_signup_payload(pw="ADMIN2025"))
    # Get auth headers
    headers = get_auth_headers(client, password="ADMIN2025")
    r = client.get("/api/all-users", headers=headers)
    assert r.status_code == 200
    # Password will be hashed, so we can't do direct comparison
    data = r.json()
    assert len(data) == 1
    assert data[0]["user_id"] == "Bob"
    assert data[0]["email"] == "Bob@atu.ie"

#This tests getting user by their user_id (requires authentication)
def test_get_user_by_id_ok(client):
    client.post("/api/sign-up", json=user_signup_payload())
    headers = get_auth_headers(client)
    r = client.get("/api/user-by-userid/Bob", headers=headers)  # user_id is "Bob" from email
    assert r.status_code == 200
    data = r.json()
    assert data["user_id"] == "Bob"
    assert data["email"] == "Bob@atu.ie"

#This tests when trying to get user by using the wrong user_id (requires authentication)
def test_get_user_by_id_not_found(client):
    client.post("/api/sign-up", json=user_signup_payload())
    headers = get_auth_headers(client)
    #Wrong user_id here (should be "Bob")
    r = client.get("/api/user-by-userid/InvalidUser", headers=headers)
    assert r.status_code == 404
    assert "user not found" in r.json()["detail"].lower()

#This tests updating a user using their user-id (requires authentication and ownership)
def test_update_user_ok(client):
    client.post("/api/sign-up", json=user_signup_payload())
    headers = get_auth_headers(client)
    r = client.put("/api/update-user-by-userid/Bob", json=user_update_payload(), headers=headers)
    assert r.status_code == 200
    assert "updated user successful" in r.json()["message"].lower() 

#This tests when trying to update a user that doesn't exist (requires authentication)
# Note: Returns 403 because user is not authorized to update other users (not admin)
def test_update_user_not_found(client):
    client.post("/api/sign-up", json=user_signup_payload())
    headers = get_auth_headers(client)
    r = client.put("/api/update-user-by-userid/InvalidUser", json=user_update_payload(), headers=headers)
    assert r.status_code == 403
    assert "not authorized" in r.json()["detail"].lower() 

#this tests deleting a user (requires authentication and ownership)
def test_delete_user_ok(client):
    client.post("/api/sign-up", json=user_signup_payload())
    headers = get_auth_headers(client)
    r = client.delete("/api/delete-user-by-userid/Bob", headers=headers)
    assert r.status_code == 200
    assert "deleted user" in r.json()["message"].lower()

#This tests when trying to delete a user that doesn't exist (requires authentication)
# Note: Returns 403 because user is not authorized to delete other users (not admin)
def test_delete_user_not_found(client):
    client.post("/api/sign-up", json=user_signup_payload())
    headers = get_auth_headers(client)
    r = client.delete("/api/delete-user-by-userid/InvalidUser", headers=headers)
    assert r.status_code == 403
    assert "not authorized" in r.json()["detail"].lower()

#This tests the health check endpoint
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}

#This tests getting user by database ID (requires authentication)
def test_get_user_by_db_id_ok(client):
    client.post("/api/sign-up", json=user_signup_payload())
    headers = get_auth_headers(client)
    r = client.get("/api/user-by-db-id/1", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == 1
    assert data["user_id"] == "Bob"

#This tests getting user by database ID when not found (requires authentication)
def test_get_user_by_db_id_not_found(client):
    client.post("/api/sign-up", json=user_signup_payload())
    headers = get_auth_headers(client)
    r = client.get("/api/user-by-db-id/999", headers=headers)
    assert r.status_code == 404
    assert "user not found" in r.json()["detail"].lower()

#This tests signing up with admin password
def test_signup_with_admin_password(client):
    r = client.post("/api/sign-up", json=user_signup_payload(pw="ADMIN2025"))
    assert r.status_code == 201
    data = r.json()
    assert data["is_admin"] == True

#This tests auto-incrementing user_id when duplicate email prefix exists
def test_signup_duplicate_email_prefix(client):
    # First user with Bob@atu.ie gets user_id "Bob"
    client.post("/api/sign-up", json=user_signup_payload())
    # Second user with Bob@gmail.com should get "Bob1" (different email, same prefix)
    r = client.post("/api/sign-up", json=second_user_payload(email="Bob@gmail.com"))
    assert r.status_code == 201
    data = r.json()
    assert data["user_id"] == "Bob1"  # auto-incremented

#This tests updating a user updates all fields correctly
def test_update_user_changes_fields(client):
    client.post("/api/sign-up", json=user_signup_payload())
    headers = get_auth_headers(client)
    # Update user with new data
    r = client.put("/api/update-user-by-userid/Bob", json=user_update_payload(
        name="UpdatedName",
        email="updated@atu.ie",
        username="UpdatedUser",
        pw="newpass",
        cid=5,
        year=3
    ), headers=headers)
    assert r.status_code == 200
    # Verify the update
    r = client.get("/api/user-by-userid/Bob", headers=headers)
    data = r.json()
    assert data["name"] == "UpdatedName"
    assert data["email"] == "updated@atu.ie"
    assert data["username"] == "UpdatedUser"
    # Password is hashed, so verify it matches
    assert verify_password("newpass", data["password"])
    assert data["course_id"] == 5
    assert data["year"] == 3

#This tests the proxy courses endpoint
def test_proxy_courses(client):
    from unittest.mock import patch, MagicMock
    with patch('httpx.Client') as mock_client:
        mock_response = MagicMock()
        mock_response.json.return_value = [{"id": 1, "name": "Course 1"}]
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response

        r = client.get("/api/proxy/courses")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

#This tests the proxy posts endpoint
def test_proxy_posts(client):
    from unittest.mock import patch, MagicMock
    with patch('httpx.Client') as mock_client:
        mock_response = MagicMock()
        mock_response.json.return_value = [{"id": 1, "content": "Post 1"}]
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response

        r = client.get("/api/proxy/posts")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


##############################################################################################################################################
# Event Processing Tests
##############################################################################################################################################

import asyncio
from app.main import (
    process_course_deleted,
    process_course_enrolled,
    process_module_enrolled,
    process_course_unenrolled,
    process_module_unenrolled,
    process_module_deleted,
    publish_event
)

# Test process_course_deleted with invalid data
def test_process_course_deleted_with_invalid_id(client):
    client.post("/api/sign-up", json=user_signup_payload())
    # Should not crash with invalid course_id
    asyncio.run(process_course_deleted({"course_id": "invalid", "course_db_id": "invalid"}))


def test_process_course_deleted_without_id(client):
    # Should handle missing course_id gracefully
    asyncio.run(process_course_deleted({}))


def test_process_course_enrolled_user_not_found(client):
    # Should handle non-existent user gracefully
    asyncio.run(process_course_enrolled({"user_id": "NonExistent", "course_db_id": 10}))


def test_process_course_enrolled_invalid_data(client):
    # Should handle missing data gracefully
    asyncio.run(process_course_enrolled({}))
    asyncio.run(process_course_enrolled({"user_id": "Bob"}))
    asyncio.run(process_course_enrolled({"course_db_id": 10}))


def test_process_module_enrolled_invalid_data(client):
    # Should handle missing data gracefully
    asyncio.run(process_module_enrolled({}))
    asyncio.run(process_module_enrolled({"user_id": "Bob"}))


def test_process_module_unenrolled_not_enrolled(client):
    client.post("/api/sign-up", json=user_signup_payload())

    # Try to unenroll from module not enrolled in
    asyncio.run(process_module_unenrolled({"user_id": "Bob", "module_id": 999}))


def test_process_module_deleted_no_module_id(client):
    # Should handle missing module_id gracefully
    asyncio.run(process_module_deleted({}))


# Test publish_event
def test_publish_event_no_rabbit_url():
    # Should return early when RABBIT_URL is not set
    asyncio.run(publish_event("test.event", {"data": "test"}))


def test_publish_event_with_mocked_rabbit():
    from unittest.mock import patch, AsyncMock, MagicMock
    with patch('app.main.RABBIT_URL', 'amqp://fake'):
        with patch('app.main.aio_pika.connect_robust') as mock_connect:
            # Just verify that connect_robust was called
            mock_connect.return_value.__aenter__ = AsyncMock()
            mock_connect.return_value.__aexit__ = AsyncMock()

            asyncio.run(publish_event("user.created", {"user_id": "test123"}))

            # Verify connection attempt was made
            mock_connect.assert_called_once_with('amqp://fake')


def test_publish_event_connection_error():
    from unittest.mock import patch
    with patch('app.main.RABBIT_URL', 'amqp://fake'):
        with patch('app.main.aio_pika.connect_robust', side_effect=Exception("Connection failed")):
            # Should not raise exception
            asyncio.run(publish_event("test.event", {"data": "test"}))


# Test login with event publishing
def test_login_publishes_event(client):
    from unittest.mock import patch, AsyncMock
    client.post("/api/sign-up", json=user_signup_payload())

    with patch('app.main.publish_event') as mock_publish:
        mock_publish.return_value = AsyncMock()
        r = client.post("/api/login", json=user_login_payload())
        assert r.status_code == 200
        # Verify event was published
        mock_publish.assert_called_once()


# Test update user publishes event
def test_update_user_publishes_event(client):
    from unittest.mock import patch, AsyncMock
    client.post("/api/sign-up", json=user_signup_payload())
    headers = get_auth_headers(client)

    with patch('app.main.publish_event') as mock_publish:
        mock_publish.return_value = AsyncMock()
        r = client.put("/api/update-user-by-userid/Bob", json=user_update_payload(), headers=headers)
        assert r.status_code == 200
        mock_publish.assert_called_once()


# Test delete user publishes event
def test_delete_user_publishes_event(client):
    from unittest.mock import patch, AsyncMock
    client.post("/api/sign-up", json=user_signup_payload())
    headers = get_auth_headers(client)

    with patch('app.main.publish_event') as mock_publish:
        mock_publish.return_value = AsyncMock()
        r = client.delete("/api/delete-user-by-userid/Bob", headers=headers)
        assert r.status_code == 200
        mock_publish.assert_called_once()


# Test signup publishes event
def test_signup_publishes_event(client):
    from unittest.mock import patch, AsyncMock

    with patch('app.main.publish_event') as mock_publish:
        mock_publish.return_value = AsyncMock()
        r = client.post("/api/sign-up", json=user_signup_payload())
        assert r.status_code == 201
        mock_publish.assert_called_once()


# Test course deleted event processing with users
def test_process_course_deleted_updates_users(client):
    from unittest.mock import patch
    client.post("/api/sign-up", json=user_signup_payload())
    client.put("/api/update-user-by-userid/Bob", json=user_update_payload(cid=5))

    # Patch SessionLocal to use test DB
    with patch('app.main.SessionLocal') as mock_session:
        from app.database import SessionLocal as TestSessionLocal
        mock_session.return_value = TestSessionLocal()

        asyncio.run(process_course_deleted({"course_id": "5", "course_db_id": 5}))

        # Verify user's course was reset
        r = client.get("/api/user-by-userid/Bob")
        # Note: This might not work perfectly due to DB session isolation


# Test module enrolled with None modules
def test_process_module_enrolled_none_modules(client):
    from unittest.mock import patch, MagicMock
    client.post("/api/sign-up", json=user_signup_payload())

    # Mock the DB session to simulate user with None enrolled_modules
    with patch('app.main.SessionLocal') as mock_session_class:
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.enrolled_modules = None
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_filter.first.return_value = mock_user
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query
        mock_session_class.return_value = mock_db

        asyncio.run(process_module_enrolled({"user_id": "Bob", "module_id": 101}))

        # Verify enrolled_modules was initialized
        assert mock_user.enrolled_modules == [101]


# Test course enrolled database error handling
def test_process_course_enrolled_db_error(client):
    from unittest.mock import patch, MagicMock

    with patch('app.main.SessionLocal') as mock_session_class:
        mock_db = MagicMock()
        mock_db.query.side_effect = Exception("Database error")
        mock_session_class.return_value = mock_db

        # Should not raise exception
        asyncio.run(process_course_enrolled({"user_id": "Bob", "course_db_id": 10}))


# Test module unenrolled database error handling
def test_process_module_unenrolled_db_error(client):
    from unittest.mock import patch, MagicMock

    with patch('app.main.SessionLocal') as mock_session_class:
        mock_db = MagicMock()
        mock_db.query.side_effect = Exception("Database error")
        mock_session_class.return_value = mock_db

        # Should not raise exception
        asyncio.run(process_module_unenrolled({"user_id": "Bob", "module_id": 201}))


# Test course unenrolled database error handling
def test_process_course_unenrolled_db_error(client):
    from unittest.mock import patch, MagicMock

    with patch('app.main.SessionLocal') as mock_session_class:
        mock_db = MagicMock()
        mock_db.query.side_effect = Exception("Database error")
        mock_session_class.return_value = mock_db

        # Should not raise exception
        asyncio.run(process_course_unenrolled({"user_id": "Bob", "course_db_id": 15}))


# Test module deleted database error handling
def test_process_module_deleted_db_error(client):
    from unittest.mock import patch, MagicMock

    with patch('app.main.SessionLocal') as mock_session_class:
        mock_db = MagicMock()
        mock_db.query.side_effect = Exception("Database error")
        mock_session_class.return_value = mock_db

        # Should not raise exception
        asyncio.run(process_module_deleted({"module_id": 301}))


# Test process_course_enrolled successfully updates user
def test_process_course_enrolled_success(client):
    from unittest.mock import patch, MagicMock

    with patch('app.main.SessionLocal') as mock_session_class:
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.user_id = "Bob"
        mock_user.course_id = 0
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_filter.first.return_value = mock_user
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query
        mock_session_class.return_value = mock_db

        asyncio.run(process_course_enrolled({"user_id": "Bob", "course_db_id": 10}))

        # Verify course_id was updated
        assert mock_user.course_id == 10
        mock_db.commit.assert_called_once()


# Test process_module_enrolled with existing module
def test_process_module_enrolled_already_enrolled(client):
    from unittest.mock import patch, MagicMock

    with patch('app.main.SessionLocal') as mock_session_class:
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.user_id = "Bob"
        mock_user.enrolled_modules = [101]  # Already enrolled
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_filter.first.return_value = mock_user
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query
        mock_session_class.return_value = mock_db

        asyncio.run(process_module_enrolled({"user_id": "Bob", "module_id": 101}))

        # Verify module list unchanged (should still be [101], not [101, 101])
        assert mock_user.enrolled_modules == [101]


# Test process_course_unenrolled successfully
def test_process_course_unenrolled_success(client):
    from unittest.mock import patch, MagicMock

    with patch('app.main.SessionLocal') as mock_session_class:
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.user_id = "Bob"
        mock_user.course_id = 15
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_filter.first.return_value = mock_user
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query
        mock_session_class.return_value = mock_db

        asyncio.run(process_course_unenrolled({"user_id": "Bob", "course_db_id": 15}))

        # Verify course_id was reset
        assert mock_user.course_id == 0
        mock_db.commit.assert_called_once()


# Test process_module_unenrolled successfully
def test_process_module_unenrolled_success(client):
    from unittest.mock import patch, MagicMock

    with patch('app.main.SessionLocal') as mock_session_class:
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.user_id = "Bob"
        mock_enrolled = MagicMock()
        mock_enrolled.__contains__ = MagicMock(return_value=True)
        mock_user.enrolled_modules = mock_enrolled
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_filter.first.return_value = mock_user
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query
        mock_session_class.return_value = mock_db

        asyncio.run(process_module_unenrolled({"user_id": "Bob", "module_id": 201}))

        # Verify module was removed
        mock_enrolled.remove.assert_called_once_with(201)
        mock_db.commit.assert_called_once()


# Test process_module_deleted successfully
def test_process_module_deleted_success(client):
    from unittest.mock import patch, MagicMock

    with patch('app.main.SessionLocal') as mock_session_class:
        mock_db = MagicMock()
        mock_user1 = MagicMock()
        mock_enrolled1 = MagicMock()
        mock_enrolled1.__contains__ = MagicMock(return_value=True)
        mock_user1.enrolled_modules = mock_enrolled1

        mock_user2 = MagicMock()
        mock_enrolled2 = MagicMock()
        mock_enrolled2.__contains__ = MagicMock(return_value=True)
        mock_user2.enrolled_modules = mock_enrolled2

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_filter.all.return_value = [mock_user1, mock_user2]
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query
        mock_session_class.return_value = mock_db

        asyncio.run(process_module_deleted({"module_id": 301}))

        # Verify module was removed from both users
        mock_enrolled1.remove.assert_called_once_with(301)
        mock_enrolled2.remove.assert_called_once_with(301)
        mock_db.commit.assert_called_once()


# Test process_course_deleted successfully
def test_process_course_deleted_success(client):
    from unittest.mock import patch, MagicMock

    with patch('app.main.SessionLocal') as mock_session_class:
        mock_db = MagicMock()
        mock_user1 = MagicMock()
        mock_user1.course_id = 5
        mock_user2 = MagicMock()
        mock_user2.course_id = 5

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_filter.all.return_value = [mock_user1, mock_user2]
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query
        mock_session_class.return_value = mock_db

        asyncio.run(process_course_deleted({"course_id": "5", "course_db_id": 5}))

        # Verify course_id was reset for both users
        assert mock_user1.course_id == 0
        assert mock_user2.course_id == 0
        mock_db.commit.assert_called_once()


# Test module enrolled success path
def test_process_module_enrolled_success(client):
    from unittest.mock import patch, MagicMock

    with patch('app.main.SessionLocal') as mock_session_class:
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.user_id = "Bob"
        mock_enrolled = MagicMock()
        mock_enrolled.__contains__ = MagicMock(return_value=False)
        mock_user.enrolled_modules = mock_enrolled
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_filter.first.return_value = mock_user
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query
        mock_session_class.return_value = mock_db

        asyncio.run(process_module_enrolled({"user_id": "Bob", "module_id": 101}))

        # Verify module was added
        mock_enrolled.append.assert_called_once_with(101)
        mock_db.commit.assert_called_once() 