from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.auth import (
    AuthResponse,
    ConfirmSignupRequest,
    LoginRequest,
    RefreshRequest,
    SignupRequest,
)
from app.services.auth_service import AuthService
from app.utils.aws import aws_helper

router = APIRouter()


@router.post("/signup", response_model=AuthResponse)
def signup(data: SignupRequest, db: Session = Depends(get_db)):
    service = AuthService(aws_helper.get_cognito(), db)
    resp = service.signup(data)
    if not resp.success:
        raise HTTPException(status_code=400, detail=resp.error)
    return resp


@router.post("/confirm-signup", response_model=AuthResponse)
def confirm(data: ConfirmSignupRequest, db: Session = Depends(get_db)):
    service = AuthService(aws_helper.get_cognito(), db)
    resp = service.confirm_signup(data)
    if not resp.success:
        raise HTTPException(status_code=400, detail=resp.error)
    return resp


@router.post("/login", response_model=AuthResponse)
def login(data: LoginRequest, response: Response, db: Session = Depends(get_db)):
    service = AuthService(aws_helper.get_cognito(), db)
    resp = service.login(data)
    if not resp.success:
        raise HTTPException(status_code=401, detail=resp.error)

    # Set cookies
    tokens = resp.model_dump() or {}
    response.set_cookie(
        "id_token",
        tokens.get("id_token", ""),
        httponly=True,
        secure=True,
        samesite="none",
    )
    response.set_cookie(
        "access_token",
        tokens.get("access_token", ""),
        httponly=True,
        secure=True,
        samesite="none",
    )
    response.set_cookie(
        "refresh_token",
        tokens.get("refresh_token", ""),
        httponly=True,
        secure=True,
        samesite="none",
    )
    return resp


@router.post("/refresh", response_model=AuthResponse)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token provided")

    service = AuthService(aws_helper.get_cognito(), db)
    resp = service.refresh(RefreshRequest(refresh_token=refresh_token))
    if not resp.success:
        raise HTTPException(status_code=401, detail=resp.error)

    tokens = resp.data or {}
    response.set_cookie(
        "id_token",
        tokens.get("id_token", ""),
        httponly=True,
        secure=True,
        samesite="none",
    )
    response.set_cookie(
        "access_token",
        tokens.get("access_token", ""),
        httponly=True,
        secure=True,
        samesite="none",
    )
    response.set_cookie(
        "refresh_token",
        tokens.get("refresh_token", ""),
        httponly=True,
        secure=True,
        samesite="none",
    )

    return resp


@router.post("/logout", response_model=AuthResponse)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    refresh_token = request.cookies.get("refresh_token")
    service = AuthService(aws_helper.get_cognito(), db)
    resp = service.logout(refresh_token=refresh_token)

    # Clear cookies
    response.delete_cookie("id_token")
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")

    return resp
