# tests/api/test_profile_api.py

import base64
import pytest
from fastapi.testclient import TestClient
from fastapi import status

from app.main import app
from app.core.deps import get_db, get_current_user, get_admin
from app.models.profile import Profile

# from app.schemas.profile import ProfileUpdate

# -------------------------------------------------------------------
# Dependency overrides for authentication
# -------------------------------------------------------------------


@pytest.fixture
def test_user(db_session):
    """Create and return a test user in the DB."""
    user = Profile(
        user_id="u1",
        username="testuser",
        email="test@example.com",
        identity_id="identity-123",
        name="Test User",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def client(test_user, db_session):
    """FastAPI TestClient with overridden auth dependencies."""

    def override_get_current_user():
        return test_user

    def override_get_db():
        yield db_session

    def override_get_admin():
        return {"sub": test_user.user_id, "cognito:groups": ["admin"]}

    app.dependency_overrides = {}
    app.dependency_overrides[get_current_user] = (  # normal user
        override_get_current_user
    )
    app.dependency_overrides[get_admin] = override_get_admin  # admin
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides = {}


# -------------------------------------------------------------------
# Tests
# -------------------------------------------------------------------


def test_api_get_profile_success(client, test_user):
    res = client.get("/api/profile")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["user_id"] == test_user.user_id
    assert data["email"] == "test@example.com"


def test_api_get_profile_not_found(client, db_session):
    # Delete user -> should 404
    db_session.query(Profile).delete()
    db_session.commit()

    res = client.get("/api/profile")
    assert res.status_code == status.HTTP_404_NOT_FOUND
    assert res.json()["detail"] == "Profile not found"


def test_api_list_profiles_as_admin(client, test_user):
    res = client.get("/api/profiles")

    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert any(u["user_id"] == test_user.user_id for u in data)


def test_api_update_profile_success(client, db_session, test_user, mock_identity):
    payload = {"username": "updated_name", "email": "updated@example.com"}
    res = client.put("api/profile", json=payload)

    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["username"] == "updated_name"
    assert data["email"] == "updated@example.com"

    # verify DB updated
    db_session.refresh(test_user)
    assert test_user.username == "updated_name"


def test_api_get_profile_image_success(client, mock_s3, test_user):
    res = client.get("/api/profile/image")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert "url" in data
    assert data["url"].startswith("https://signed.example/")


def test_api_get_profile_image_not_found(client, db_session):
    db_session.query(Profile).delete()
    db_session.commit()
    res = client.get("/api/profile/image")
    assert res.status_code == status.HTTP_404_NOT_FOUND
    assert res.json()["detail"] == "Profile not found"


def test_api_upload_profile_image_success(client, mock_s3, test_user):
    fake_image = base64.b64encode(b"fake image data").decode("utf-8")
    payload = {"image": fake_image, "content_type": "image/jpeg"}
    res = client.post("api/profile/image", json=payload)

    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["message"] == "Profile image uploaded successfully"
    assert data["s3_key"].endswith(".jpg")

    # verify DB updated
    assert test_user.profile_image_key == data["s3_key"]


def test_api_upload_profile_image_invalid_base64(client, test_user):
    payload = {"image": "!!!not_base64!!!", "content_type": "image/jpeg"}
    res = client.post("api/profile/image", json=payload)

    assert res.status_code == status.HTTP_400_BAD_REQUEST
    assert res.json()["detail"] == "Invalid base64 image data"


def test_api_upload_profile_image_not_found(client, db_session):
    db_session.query(Profile).delete()
    db_session.commit()
    fake_image = base64.b64encode(b"fake").decode("utf-8")
    payload = {"image": fake_image, "content_type": "image/jpeg"}
    res = client.post("api/profile/image", json=payload)

    assert res.status_code == status.HTTP_404_NOT_FOUND
    assert res.json()["detail"] == "Profile not found"
