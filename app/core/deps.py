from fastapi import Depends, HTTPException, Request, status
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import verify_jwt
from app.db.session import get_db
from app.models.profile import Profile


def get_claims(request: Request):
    # 1. Try to get token from cookie
    token = request.cookies.get("access_token")

    # fallback: Authorization header
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
        )

    # 2. Verify token
    try:
        claims = verify_jwt(token, audience=settings.CLIENT_ID, token_use="access")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    return claims


def get_current_user(request: Request, db: Session = Depends(get_db)) -> Profile:
    """
    Dependency that extracts and verifies the current user from JWT in cookies.
    """
    claims = get_claims(request)
    user_sub = claims.get("sub")
    if not user_sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: no subject claim",
        )

    user = db.query(Profile).filter(Profile.user_id == user_sub).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    return user


def get_admin(request: Request):
    """
    FastAPI dependency to enforce admin access.
    Validates the JWT, checks for "admin" group.
    """
    claims = get_claims(request)

    groups = claims.get("cognito:groups", [])
    if "admin" not in groups:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    return claims
