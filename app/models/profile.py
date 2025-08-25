import enum

from sqlalchemy import Column, DateTime, Enum, Integer, String
from sqlalchemy.sql import func

from app.db.base import Base


class GenderEnum(str, enum.Enum):
    male = "male"
    female = "female"
    other = "other"


class Profile(Base):
    __tablename__ = "profiles"

    user_id = Column(String, primary_key=True, index=True)  # Could use UUID
    name = Column(String, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)

    dob = Column(DateTime, nullable=True)
    gender = Column(Enum(GenderEnum), nullable=True)
    height = Column(Integer, nullable=True)

    identity_id = Column(String, nullable=True)
    profile_image_key = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
