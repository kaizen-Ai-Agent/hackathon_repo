import jwt
from datetime import datetime, timedelta
from typing import Optional
from .config import Settings


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Create a signed JWT access token
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=Settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})

    encoded_jwt = jwt.encode(
        to_encode, Settings.JWT_SECRET_KEY, algorithm=Settings.JWT_ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(data: dict):
    """
    Create a signed JWT refresh token
    """
    expire = datetime.utcnow() + timedelta(days=Settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {**data, "exp": expire, "type": "refresh"}
    return jwt.encode(
        to_encode, Settings.JWT_SECRET_KEY, algorithm=Settings.JWT_ALGORITHM
    )


def decode_token(token: str):
    """
    Decode and validate a JWT token.
    Returns the decoded payload or raises jwt exceptions.
    """
    try:
        payload = jwt.decode(
            token, Settings.JWT_SECRET_KEY, algorithms=[Settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")
