# tests/services/test_auth_service.py
import pytest
from unittest.mock import Mock
from botocore.exceptions import ClientError
from requests.exceptions import HTTPError

from app.schemas.auth import (
    ConfirmSignupRequest,
    LoginRequest,
    RefreshRequest,
    SignupRequest,
)
from app.core.config import settings
from app.models.profile import Profile


def test_signup_success(auth_service, mock_cognito):
    # Cognito returns dict-like response (not a Mock)
    mock_cognito.sign_up.return_value = {"UserSub": "fake-sub-123"}

    req = SignupRequest(
        username="testuser",
        password="Pass123!",
        email="test@example.com",
        name="Test User",
    )
    resp = auth_service.signup(req)

    assert resp.success is True
    assert resp.data["user_sub"] == "fake-sub-123"
    assert resp.username == "testuser"
    assert resp.email == "test@example.com"

    # Verify DB row was created (auth_service.db is the session)
    created = auth_service.db.query(Profile).filter_by(user_id="fake-sub-123").one_or_none()
    assert created is not None
    assert created.username == "testuser"


def test_signup_failure(auth_service, mock_cognito):
    mock_cognito.sign_up.side_effect = Exception("AWS error")

    req = SignupRequest(
        username="testuser2",
        password="pw",
        email="a@test.com",
        name="A B",
    )
    resp = auth_service.signup(req)

    assert resp.success is False
    assert "AWS error" in (resp.error or "")


def test_confirm_signup_success(auth_service, mock_cognito):
    # confirm_sign_up typically returns None on success; just ensure no exception
    mock_cognito.confirm_sign_up.return_value = None

    req = ConfirmSignupRequest(username="testuser", code="123456")
    resp = auth_service.confirm_signup(req)

    assert resp.success is True

    # Assert it was called with expected keyword args (check minimal/important ones)
    args, kwargs = mock_cognito.confirm_sign_up.call_args
    assert kwargs["ClientId"] == settings.CLIENT_ID
    assert kwargs["Username"] == "testuser"
    assert kwargs["ConfirmationCode"] == "123456"


def test_confirm_signup_failure(auth_service, mock_cognito):
    # Simulate Cognito ClientError
    err = {"Error": {"Message": "Invalid code", "Code": "400"}}
    mock_cognito.confirm_sign_up.side_effect = ClientError(err, "ConfirmSignUp")

    req = ConfirmSignupRequest(username="testuser", code="badcode")
    resp = auth_service.confirm_signup(req)

    assert resp.success is False
    assert "Confirm failed" in resp.message


def test_login_success(auth_service, mock_cognito, monkeypatch):
    # Service uses admin_initiate_auth
    mock_cognito.admin_initiate_auth.return_value = {
        "AuthenticationResult": {
            "IdToken": "id123",
            "AccessToken": "acc123",
            "RefreshToken": "ref123",
        }
    }

    # Patch verify_jwt used in the service to return expected claims
    monkeypatch.setattr(
        "app.services.auth_service.verify_jwt",
        lambda token, audience, token_use: {
            "cognito:username": "testuser",
            "email": "test@example.com",
            "cognito:groups": ["g1"],
        },
    )

    req = LoginRequest(username="testuser", password="pw")
    resp = auth_service.login(req)

    assert resp.success is True
    assert resp.id_token == "id123"
    assert resp.access_token == "acc123"
    assert resp.refresh_token == "ref123"
    assert resp.username == "testuser"
    assert resp.email == "test@example.com"
    assert resp.groups == ["g1"]


def test_login_invalid(auth_service, mock_cognito):
    mock_cognito.admin_initiate_auth.side_effect = Exception("NotAuthorized")

    req = LoginRequest(username="a@test.com", password="bad")
    resp = auth_service.login(req)

    assert resp.success is False
    assert "NotAuthorized" in (resp.error or "")


def test_refresh_success(auth_service, monkeypatch):
    # Fake response object for requests.post
    fake_response = Mock()
    fake_response.json.return_value = {
        "id_token": "id_new",
        "access_token": "acc_new",
        "refresh_token": "ref_new",
    }
    fake_response.raise_for_status = lambda: None  # no-op

    # Patch requests.post used by service
    monkeypatch.setattr(
        "app.services.auth_service.requests.post", lambda *a, **kw: fake_response
    )

    req = RefreshRequest(refresh_token="ref_old")
    resp = auth_service.refresh(req)

    assert resp.success is True
    assert resp.data["id_token"] == "id_new"
    assert resp.data["access_token"] == "acc_new"
    assert resp.data["refresh_token"] == "ref_new"


def test_refresh_failure_http_error(auth_service, monkeypatch):
    fake_response = Mock()
    def raise_err():
        raise HTTPError("Bad request")
    fake_response.raise_for_status = raise_err

    monkeypatch.setattr(
        "app.services.auth_service.requests.post", lambda *a, **kw: fake_response
    )

    req = RefreshRequest(refresh_token="ref_old")
    resp = auth_service.refresh(req)

    assert resp.success is False
    assert "Bad request" in (resp.error or "")


def test_logout_success(auth_service, mock_cognito):
    mock_cognito.revoke_token.return_value = {}

    resp = auth_service.logout(refresh_token="ref123")

    assert resp.success is True

    # assert the token was passed; be tolerant about ClientSecret presence
    mock_cognito.revoke_token.assert_called_once()
    _, kwargs = mock_cognito.revoke_token.call_args
    assert kwargs["Token"] == "ref123"
    assert kwargs["ClientId"] == settings.CLIENT_ID
    # If your code includes ClientSecret only when present, assert accordingly:
    if settings.CLIENT_SECRET:
        assert kwargs.get("ClientSecret") == settings.CLIENT_SECRET
