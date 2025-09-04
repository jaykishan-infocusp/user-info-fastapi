# tests/api/test_auth.py
from tests.factories.auth import (ConfirmSignupRequestFactory,
                                  SignupRequestFactory)
from botocore.exceptions import ClientError


def test_api_signup_success(client, mock_cognito, fake_tokens):
    # Cognito returns a dict with UserSub
    mock_cognito.sign_up.return_value = {"UserSub": "fake-user-sub"}

    payload = SignupRequestFactory().dict()
    res = client.post("/signup", json=payload)

    assert res.status_code == 200
    body = res.json()

    # Verify response from AuthResponse
    assert body["success"] is True
    assert body["data"]["user_sub"] == "fake-user-sub"
    assert body["username"] == payload["username"]
    assert body["email"] == payload["email"]

    mock_cognito.sign_up.assert_called_once()


def test_api_confirm_signup_failure(client, mock_cognito):
    error_response = {
        "Error": {
            "Code": "NotAuthorizedException",
            "Message": "Invalid code"
        }
    }
    mock_cognito.confirm_sign_up.side_effect = ClientError(error_response, "ConfirmSignUp")

    payload = ConfirmSignupRequestFactory().dict()
    res = client.post("/confirm-signup", json=payload)

    assert res.status_code == 400
    assert "Invalid code" in res.json()["detail"]


# def test_api_login_sets_cookies(client, mock_cognito, fake_tokens):
#     mock_cognito.admin_initiate_auth.return_value = {"success": True, "model_dump": lambda: fake_tokens}

#     res = client.post("/login", data={"username": "testuser", "password": "TestPswd!"})

#     assert res.status_code == 200
#     assert res.cookies.get("id_token") == "fake-id"
#     assert res.cookies.get("refresh_token") == "fake-refresh"


def test_api_refresh_requires_cookie(client):
    res = client.post("/refresh")
    assert res.status_code == 401
    assert res.json()["detail"] == "No refresh token provided"


def test_api_logout_clears_cookies(client, mock_cognito):
    mock_cognito.logout.return_value = type("Resp", (), {"success": True, "model_dump": lambda: {}})

    res = client.post("/logout", cookies={"refresh_token": "fake-refresh"})

    assert res.status_code == 200
    assert "id_token" not in res.cookies
    assert "refresh_token" not in res.cookies
