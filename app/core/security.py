import base64
import hashlib
import hmac
import time

import requests
from jose import JWTError, jwt

from app.core.config import settings
from app.utils.aws import aws_helper


JWKS = None
JWKS_LAST_FETCH = None


def get_jwks():
    global JWKS, JWKS_LAST_FETCH
    if JWKS and JWKS_LAST_FETCH and time.time() - JWKS_LAST_FETCH < settings.JWKS_TTL:
        return JWKS
    jwks_url = (
        f"https://cognito-idp.{settings.AWS_REGION_NAME}.amazonaws.com/"
        f"{settings.USER_POOL_ID}/.well-known/jwks.json"
    )
    resp = requests.get(jwks_url)
    resp.raise_for_status()
    JWKS = resp.json()
    JWKS_LAST_FETCH = time.time()
    return JWKS


def verify_jwt(token, audience, token_use):
    jwks = get_jwks()
    try:
        header = jwt.get_unverified_header(token)
        key = next(k for k in jwks["keys"] if k["kid"] == header["kid"])
        claims = jwt.decode(
            token,
            key,
            audience=audience,
            issuer=(
                f"https://cognito-idp.{settings.AWS_REGION_NAME}.amazonaws.com/"
                f"{settings.USER_POOL_ID}"
            ),
            options={"verify_aud": True},
        )
        if claims.get("token_use") != token_use:
            raise JWTError(f"Invalid token_use: {claims.get('token_use')}")
        return claims
    except StopIteration:
        raise JWTError("Public key not found")
    except Exception as e:
        raise e


def get_cookie(event, name):
    # HTTP API (v2) style
    if event.cookies and isinstance(event.cookies, list):
        for cookie in event.cookies:
            if cookie.startswith(f"{name}="):
                return cookie.split("=", 1)[1]
    elif event.cookies and isinstance(event.cookies, dict):
        return event.cookies.get(name) or None
    # REST API (v1) style
    elif "headers" in event and "cookie" in event["headers"]:
        cookies = event["headers"]["cookie"].split("; ")
        for cookie in cookies:
            if cookie.startswith(f"{name}="):
                return cookie.split("=", 1)[1]
    return None


def get_cognito_identity_id(event):
    """Returns the Cognito Identity Pool ID for the currently logged-in user."""
    id_token = get_cookie(event, "id_token")
    if not id_token:
        raise ValueError("Missing ID token in cookies")

    cognito_identity = aws_helper.get_cognito_identity()

    identity_response = cognito_identity.get_id(
        IdentityPoolId=settings.IDENTITY_POOL_ID,
        Logins={
            f"cognito-idp.{settings.AWS_REGION_NAME}.amazonaws.com/{settings.USER_POOL_ID}": id_token
        },
    )
    return identity_response["IdentityId"]


def secret_hash(username: str) -> str:
    message = username + settings.CLIENT_ID
    dig = hmac.new(
        str(settings.CLIENT_SECRET).encode("utf-8"),
        msg=message.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    return base64.b64encode(dig).decode()
