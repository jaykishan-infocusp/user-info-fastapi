# app/db/base.py
from sqlalchemy.orm import DeclarativeBase


# This will be the base class for all your models
class Base(DeclarativeBase):
    pass
