from unittest.mock import Mock

import pytest

from app.services.profile_service import ProfileService

@pytest.fixture
def profile_service():
    return ProfileService()


@pytest.fixture
def mock_s3(mocker):
    """
    Patch aws_helper.get_s3 used by app.services.profile_service.
    Return a Mock S3 client with generate_presigned_url and put_object methods.
    """
    fake_s3 = Mock()
    fake_s3.generate_presigned_url.return_value = "https://signed.example/profile.png"
    fake_s3.put_object.return_value = {}
    # Patch where ProfileService imports aws_helper
    mocker.patch("app.services.profile_service.aws_helper.get_s3", return_value=fake_s3)
    return fake_s3


@pytest.fixture
def mock_identity(mocker):
    """
    Patch get_cognito_identity_id imported inside profile_service module.
    Default: return 'identity-123'. Tests can override via monkeypatch if needed.
    """
    mocker.patch("app.services.profile_service.get_cognito_identity_id", return_value="identity-123")
    return "identity-123"
