# app/services/profile_service.py
import base64
import time
from typing import List

from botocore.exceptions import ClientError
from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_cognito_identity_id
from app.models.profile import Profile as ProfileModel
from app.schemas.profile import ProfileUpdate
from app.utils.aws import aws_helper


class ProfileService:
    def get_profile(self, db: Session, user_id: str) -> ProfileModel:
        profile = db.query(ProfileModel).filter(ProfileModel.user_id == user_id).first()
        if not profile:
            return None
        return profile

    def list_profiles(self, db: Session) -> List[ProfileModel]:
        return db.query(ProfileModel).all()

    def update_profile(
        self, request: Request, db: Session, user_id: str, updates: ProfileUpdate
    ) -> ProfileModel:
        profile = db.query(ProfileModel).filter(ProfileModel.user_id == user_id).first()

        # Step 1: Try to get Cognito Identity ID (may not exist at signup)
        identity_id = None
        try:
            identity_id = get_cognito_identity_id(request)
        except Exception as ex:
            # not fatal; we just won’t store it yet
            pass
        if not profile:
            profile = ProfileModel(user_id=user_id)
            db.add(profile)
        profile.identity_id = identity_id

        for key, value in updates.model_dump(exclude_unset=True).items():
            setattr(profile, key, value)

        db.commit()
        db.refresh(profile)
        return profile

    def get_profile_image(self, db: Session, user_id: str) -> dict:
        """
        Returns a presigned URL for the authenticated user's profile image.
        """
        profile = self.get_profile(db, user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")

        s3_client = aws_helper.get_s3()
        image_key = profile.profile_image_key or f"{profile.identity_id}/profile.png"

        try:
            url = s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": settings.S3_BUCKET_NAME, "Key": image_key},
                ExpiresIn=3600,  # 1 hour
            )
        except ClientError as e:
            raise HTTPException(status_code=500, detail=f"S3 error: {e}")

        return {"url": url}

    def upload_profile_image_base64(
        self,
        db: Session,
        user_id: str,
        image_base64: str,
        content_type: str = "image/jpeg",
    ) -> dict:
        """
        Uploads a base64-encoded profile image to S3 and updates the user's profile record in Postgres.
        """
        profile = self.get_profile(db, user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")

        # Decode base64
        try:
            image_data = base64.b64decode(image_base64)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid base64 image data")

        s3_client = aws_helper.get_s3()
        s3_key = f"{profile.identity_id}/profile-{int(time.time())}.jpg"

        try:
            s3_client.put_object(
                Bucket=settings.S3_BUCKET_NAME,
                Key=s3_key,
                Body=image_data,
                ContentType=content_type,
            )
        except ClientError as e:
            raise HTTPException(status_code=500, detail=f"S3 upload error: {e}")

        # Update DB
        profile.profile_image_key = s3_key
        db.add(profile)
        db.commit()
        db.refresh(profile)

        return {"message": "Profile image uploaded successfully", "s3_key": s3_key}
