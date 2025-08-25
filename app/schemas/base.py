# app/schemas/base.py
from typing import Any, Optional

from pydantic import BaseModel


class BaseRequest(BaseModel):
    """Base request schema all services should extend."""

    pass


class BaseResponse(BaseModel):
    """Base response schema with status, message, and data."""

    success: bool
    message: str
    data: Optional[Any] = None
    error: Optional[str] = None
