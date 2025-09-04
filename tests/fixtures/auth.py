# tests/fixtures/auth.py
import pytest

from app.services.auth_service import AuthService

@pytest.fixture
def mock_cognito(mocker):
    """Mock AWS Cognito client used inside AuthService."""
    mock_cognito = mocker.Mock()
    mocker.patch("app.utils.aws.aws_helper.get_cognito", return_value=mock_cognito)
    return mock_cognito

@pytest.fixture
def fake_tokens():
    return {
        "id_token": "fake-id",
        "access_token": "fake-access",
        "refresh_token": "fake-refresh",
    }


@pytest.fixture
def auth_service(mock_cognito, db_session):
    return AuthService(mock_cognito, db_session)