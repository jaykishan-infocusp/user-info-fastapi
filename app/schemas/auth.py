# app/schemas/auth.py
from pydantic import EmailStr

from app.schemas.base import BaseRequest, BaseResponse


class SignupRequest(BaseRequest):
    username: str
    password: str
    email: EmailStr
    name: str


class ConfirmSignupRequest(BaseRequest):
    username: str
    code: str


class LoginRequest(BaseRequest):
    username: str
    password: str


class RefreshRequest(BaseRequest):
    refresh_token: str


class AuthResponse(BaseResponse):
    access_token: str | None = None
    id_token: str | None = None
    refresh_token: str | None = None
    username: str | None = None
    email: str | None = None
    groups: list[str] | None = None
