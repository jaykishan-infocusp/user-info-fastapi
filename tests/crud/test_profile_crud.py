# tests/services/test_profile_service.py
import base64
from unittest.mock import Mock

import pytest
from botocore.exceptions import ClientError
from fastapi import HTTPException

from app.schemas.profile import ProfileUpdate
from tests.factories.profile import ProfileFactory


def test_get_profile_found_and_not_found(db_session, profile_service):
    # create
    p1 = ProfileFactory(user_id="u1", username="u1name", email="u1@example.com")

    db_session.flush()
    found = profile_service.get_profile(db_session, "u1")

    assert found is not None
    assert found.user_id == "u1"
    assert found.email == "u1@example.com"

    # not found
    assert profile_service.get_profile(db_session, "missing") is None


def test_list_profiles(db_session, profile_service):
    ProfileFactory.create_batch(3)
    db_session.flush()

    all_profiles = profile_service.list_profiles(db_session)
    assert len(all_profiles) >= 3


def test_update_profile_creates_new_when_missing(db_session, profile_service, mocker):
    # ensure get_cognito_identity_id returns a value
    mocker.patch("app.services.profile_service.get_cognito_identity_id", return_value="identity-xyz")

    updates = ProfileUpdate(name="New Name", username="newuser", email="new@example.com", height=180)
    # request object can be simple mock, since get_cognito_identity_id is patched above
    fake_request = Mock()
    profile = profile_service.update_profile(fake_request, db_session, user_id="new-user", updates=updates)

    assert profile is not None
    assert profile.user_id == "new-user"
    assert profile.identity_id == "identity-xyz"
    assert profile.name == "New Name"
    assert profile.email == "new@example.com"


def test_update_profile_identity_missing_does_not_fail(db_session, profile_service, mocker):
    # make get_cognito_identity_id raise to simulate missing identity
    mocker.patch("app.services.profile_service.get_cognito_identity_id", side_effect=Exception("no identity"))

    updates = ProfileUpdate(name="N", username="currentuser", email="n@example.com")
    profile = profile_service.update_profile(Mock(), db_session, user_id="u2", updates=updates)

    assert profile is not None
    assert profile.user_id == "u2"
    assert profile.identity_id is None


def test_get_profile_image_success(db_session, profile_service, mock_s3):
    p = ProfileFactory(user_id="uimg", username="uimgname", email="img@example.com", identity_id="identity-1")
    db_session.flush()
    resp = profile_service.get_profile_image(db_session, "uimg")
    assert "url" in resp
    assert resp["url"].startswith("https://signed.example")


def test_get_profile_image_no_profile(db_session, profile_service):
    with pytest.raises(HTTPException) as exc:
        profile_service.get_profile_image(db_session, "does-not-exist")
    assert exc.value.status_code == 404


def test_get_profile_image_s3_failure(db_session, profile_service, mock_s3, mocker):
    p = ProfileFactory(user_id="uimg2", username="uimg2", email="img2@example.com", identity_id="identity-2")
    db_session.flush()

    # make generate_presigned_url raise ClientError
    mock_s3.generate_presigned_url.side_effect = ClientError({"Error": {}}, "GetObject")
    with pytest.raises(HTTPException) as exc:
        profile_service.get_profile_image(db_session, "uimg2")
    assert exc.value.status_code == 500


def test_upload_profile_image_base64_success(db_session, profile_service, mock_s3):
    p = ProfileFactory(user_id="uup", username="uupname", email="up@example.com", identity_id="identity-up")
    db_session.flush()

    # create valid small base64
    raw = b"fake-image-binary"
    image_b64 = base64.b64encode(raw).decode("ascii")
    res = profile_service.upload_profile_image_base64(db_session, "uup", image_b64, content_type="image/png")

    assert res["message"].lower().startswith("profile image uploaded")
    s3_key = res["s3_key"]
    assert s3_key.startswith("identity-up/profile-") and s3_key.endswith(".jpg")

    # confirm DB was updated
    db_session.refresh(p)
    assert p.profile_image_key == s3_key

    # ensure put_object called with correct bucket/key/body
    mock_s3.put_object.assert_called_once()
    args, kwargs = mock_s3.put_object.call_args

    assert kwargs["Bucket"] == pytest.importorskip("app").core.config.settings.S3_BUCKET_NAME  # verify bucket from settings
    assert kwargs["Key"] == s3_key
    assert kwargs["Body"] == raw
    assert kwargs["ContentType"] == "image/png"


def test_upload_profile_image_invalid_base64(db_session, profile_service):
    p = ProfileFactory(user_id="uup2", username="uup2name", email="uup2@example.com", identity_id="identity-up2")
    db_session.flush()

    with pytest.raises(HTTPException) as exc:
        profile_service.upload_profile_image_base64(db_session, "uup2", "not-a-base64", content_type="image/png")
    assert exc.value.status_code == 400


def test_upload_profile_image_s3_error(db_session, profile_service, mock_s3):
    p = ProfileFactory(user_id="uup3", username="uup3", email="uup3@example.com", identity_id="identity-up3")
    db_session.flush()

    # s3 put_object raises
    mock_s3.put_object.side_effect = ClientError({"Error": {}}, "PutObject")
    with pytest.raises(HTTPException) as exc:
        profile_service.upload_profile_image_base64(db_session, "uup3", base64.b64encode(b"x").decode("ascii"))
    assert exc.value.status_code == 500
