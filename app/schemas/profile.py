# app/schemas/profile.py
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr


class ProfileBase(BaseModel):
    email: Optional[EmailStr] = None
    username: str
    name: Optional[str] = None
    height: Optional[int] = None
    gender: Optional[str] = None
    dob: Optional[date] = None
    profile_image_key: Optional[str] = None


class ProfileUpdate(ProfileBase):
    pass


class Profile(ProfileBase):
    user_id: str
    identity_id: Optional[str] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class UploadProfileImageRequest(BaseModel):
    image: str
    content_type: Optional[str] = "image/jpeg"


class ProfileImageResponse(BaseModel):
    url: str


class ProfileImageUploadResponse(BaseModel):
    message: str
    s3_key: str
