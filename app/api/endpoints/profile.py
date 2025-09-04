# app/api/profile.py
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.deps import get_admin, get_current_user
from app.db.session import get_db
from app.schemas.profile import (
    Profile,
    ProfileImageResponse,
    ProfileImageUploadResponse,
    ProfileUpdate,
    UploadProfileImageRequest,
)
from app.services.profile_service import ProfileService

router = APIRouter()
service = ProfileService()


@router.get("/profile", response_model=Profile)
def get_profile(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """
    Get the authenticated user's profile.
    """
    logging.info(f"Getting profile details for {current_user.username}")
    profile = service.get_profile(db, current_user.user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.get(
    "/profiles",
    response_model=List[Profile],
)
def list_profiles(
    db: Session = Depends(get_db),
    admin_claims: dict = Depends(get_admin),
):
    """
    List all profiles (admin only).
    """
    logging.info("Getting all user details")
    profiles = service.list_profiles(db)
    return profiles


@router.put("/profile", response_model=Profile)
def update_profile(
    request: Request,
    data: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Update authenticated user's profile.
    """
    logging.info(f"Updating profile for {current_user.username}")
    profile = service.update_profile(request, db, current_user.user_id, data)
    return profile


@router.get("/profile/image", response_model=ProfileImageResponse)
def get_profile_image(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Returns a presigned URL for the user's profile image.
    """
    logging.info(f"Getting profile image for {current_user.username}")
    return service.get_profile_image(db, user_id=current_user.user_id)


@router.post("/profile/image", response_model=ProfileImageUploadResponse)
def upload_profile_image(
    payload: UploadProfileImageRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    logging.info(f"Updating profile image for {current_user.username}")
    return service.upload_profile_image_base64(
        db,
        user_id=current_user.user_id,
        image_base64=payload.image,
        content_type=payload.content_type,
    )
