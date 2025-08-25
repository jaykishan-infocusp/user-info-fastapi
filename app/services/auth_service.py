from datetime import datetime
from typing import Optional

import requests
from botocore.exceptions import ClientError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import secret_hash, verify_jwt
from app.models.profile import Profile
from app.schemas.auth import (
    AuthResponse,
    ConfirmSignupRequest,
    LoginRequest,
    RefreshRequest,
    SignupRequest,
)


class AuthService:
    def __init__(self, cognito_client, db: Session):
        self.cognito = cognito_client
        self.db = db

    # ---------------------------
    # Signup
    # ---------------------------
    def signup(self, request: SignupRequest) -> AuthResponse:
        try:
            response = self.cognito.sign_up(
                ClientId=settings.CLIENT_ID,
                Username=request.username,
                Password=request.password,
                SecretHash=secret_hash(request.username),
                UserAttributes=[
                    {"Name": "email", "Value": request.email},
                    {"Name": "name", "Value": request.name},
                ],
            )
        except Exception as e:
            return AuthResponse(success=False, message="Signup failed", error=str(e))

        user_sub = response["UserSub"]

        # persist to Postgres
        user = Profile(
            user_id=user_sub,
            username=request.username,
            email=request.email,
            name=request.name,
            created_at=datetime.utcnow(),
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        return AuthResponse(
            success=True,
            message="User signed up successfully",
            data={"user_sub": user_sub},
            username=request.username,
            email=request.email,
        )

    # ---------------------------
    # Confirm Signup
    # ---------------------------
    def confirm_signup(self, request: ConfirmSignupRequest) -> AuthResponse:
        try:
            self.cognito.confirm_sign_up(
                ClientId=settings.CLIENT_ID,
                Username=request.username,
                ConfirmationCode=request.code,
                SecretHash=secret_hash(request.username),
            )
            return AuthResponse(success=True, message="User confirmed successfully")
        except ClientError as e:
            return AuthResponse(success=False, message="Confirm failed", error=str(e))

    # ---------------------------
    # Login
    # ---------------------------
    def login(self, request: LoginRequest) -> AuthResponse:
        try:
            resp = self.cognito.admin_initiate_auth(
                UserPoolId=settings.USER_POOL_ID,
                ClientId=settings.CLIENT_ID,
                AuthFlow="ADMIN_NO_SRP_AUTH",
                AuthParameters={
                    "USERNAME": request.username,
                    "PASSWORD": request.password,
                    "SECRET_HASH": secret_hash(request.username),
                },
            )

            auth_result = resp["AuthenticationResult"]

            claims = verify_jwt(
                auth_result["IdToken"], audience=settings.CLIENT_ID, token_use="id"
            )

            return AuthResponse(
                success=True,
                message="Login successful",
                id_token=auth_result["IdToken"],
                access_token=auth_result["AccessToken"],
                refresh_token=auth_result["RefreshToken"],
                username=claims.get("cognito:username"),
                email=claims.get("email"),
                groups=claims.get("cognito:groups", []),
            )
        except Exception as e:
            return AuthResponse(success=False, message="Login failed", error=str(e))

    # ---------------------------
    # Refresh
    # ---------------------------
    def refresh(self, request: RefreshRequest) -> AuthResponse:
        token_url = f"https://{settings.COGNITO_DOMAIN}/oauth2/token"
        payload = {
            "grant_type": "refresh_token",
            "client_id": settings.CLIENT_ID,
            "refresh_token": request.refresh_token,
        }
        auth = None
        if settings.CLIENT_SECRET:
            from requests.auth import HTTPBasicAuth

            auth = HTTPBasicAuth(settings.CLIENT_ID, settings.CLIENT_SECRET)

        try:
            r = requests.post(
                token_url,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                auth=auth,
                timeout=5,
            )
            r.raise_for_status()
            new_tokens = r.json()

            return AuthResponse(
                success=True,
                message="Tokens refreshed",
                data={
                    "id_token": new_tokens.get("id_token"),
                    "access_token": new_tokens.get("access_token"),
                    "refresh_token": new_tokens.get(
                        "refresh_token", request.refresh_token
                    ),
                },
            )
        except Exception as e:
            return AuthResponse(
                success=False, message="Token refresh failed", error=str(e)
            )

    # ---------------------------
    # Logout
    # ---------------------------
    def logout(self, refresh_token: Optional[str] = None) -> AuthResponse:
        # Optionally revoke token
        if refresh_token:
            try:
                self.cognito.revoke_token(
                    Token=refresh_token,
                    ClientId=settings.CLIENT_ID,
                    ClientSecret=settings.CLIENT_SECRET or None,
                )
            except Exception:
                pass  # don't fail logout if revocation fails

        return AuthResponse(success=True, message="Logged out")
