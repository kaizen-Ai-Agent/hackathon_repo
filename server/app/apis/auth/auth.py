from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import JSONResponse
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from urllib.parse import urlencode
import requests as http_requests
import secrets
import logging
from datetime import datetime, timezone, timedelta
from core.config import Settings
from core.security import create_access_token, decode_token, create_refresh_token
from db.prisma_client import prisma, Prisma
from db.redis_client import RedisClient
from models.schema import UserOut

logger = logging.getLogger(__name__)
auth_router = APIRouter(prefix="/auth/google", tags=["Google OAuth"])


# ------------------------------------------------------------
# 1️⃣ Generate Google OAuth URL
# ------------------------------------------------------------
@auth_router.get("/url")
async def google_oauth_url():
    """
    Generate Google OAuth authorization URL (now includes Google Calendar scope).
    """
    try:
        state = secrets.token_urlsafe(32)
        await RedisClient.set(f"{Settings.GOOGLE_OAUTH_STATE_KEY}:{state}", "valid")

        params = {
            "client_id": Settings.GOOGLE_OAUTH2_CLIENT_ID,
            "redirect_uri": Settings.GOOGLE_OAUTH2_REDIRECT_URI,
            "scope": "openid email profile https://www.googleapis.com/auth/calendar",
            "response_type": "code",
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }

        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

        return JSONResponse({"auth_url": auth_url, "state": state})

    except Exception as e:
        logger.error(f"Error generating OAuth URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate OAuth URL")


# ------------------------------------------------------------
# 2️⃣ Handle OAuth Callback
# ------------------------------------------------------------
@auth_router.get("/callback")
async def google_oauth_callback(request: Request):
    """
    Handle Google OAuth callback: verify tokens, create user, store in Prisma.
    """
    try:
        # Extract query params from redirect
        code = request.query_params.get("code")
        state = request.query_params.get("state")

        if not code:
            raise HTTPException(
                status_code=400, detail="Authorization code is required"
            )

        saved_state = await RedisClient.get(
            f"{Settings.GOOGLE_OAUTH_STATE_KEY}:{state}"
        )
        if not saved_state:
            raise HTTPException(status_code=400, detail="Invalid state parameter")

        token_data = exchange_code_for_tokens(code)

        if not token_data:
            raise HTTPException(
                status_code=400, detail="Failed to exchange code for tokens"
            )

        # Verify Google ID token
        user_info = verify_google_token(token_data.get("id_token"))
        if not user_info:
            raise HTTPException(status_code=400, detail="Invalid Google token")

        await prisma.connect()
        user, created = await get_or_create_google_user(user_info, token_data)
        await prisma.disconnect()

        tokens = {
            "access_token": token_data.get("access_token"),
            "refresh_token": token_data.get("refresh_token"),
            "expires_in": token_data.get("expires_in"),
        }
        payload = {
            "sub": str(user.id),
            "email": user.email,
            "name": user.name,
        }

        access_token = create_access_token(payload)
        refresh_token = create_refresh_token(payload)

        return JSONResponse(
            {
                "status": "success",
                "user": UserOut(
                    id=user.id,
                    email=user.email,
                    name=user.name,
                ).dict(),
                "is_new_user": created,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
            }
        )

    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        raise HTTPException(status_code=500, detail="OAuth authentication failed")


# ------------------------------------------------------------
# 3️⃣ Token & Verification Utilities
# ------------------------------------------------------------
def exchange_code_for_tokens(code: str):
    """Exchange authorization code for access and ID tokens"""
    try:
        token_url = "https://oauth2.googleapis.com/token"

        data = {
            "client_id": Settings.GOOGLE_OAUTH2_CLIENT_ID,
            "client_secret": Settings.GOOGLE_OAUTH2_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": Settings.GOOGLE_OAUTH2_REDIRECT_URI,
        }

        resp = http_requests.post(token_url, data=data)
        if resp.status_code == 200:
            return resp.json()
        logger.error(f"Token exchange failed: {resp.text}")
        return None

    except Exception as e:
        logger.error(f"Error exchanging code: {e}")
        return None


def verify_google_token(id_token_str: str):
    """Verify Google ID token and extract user info"""
    try:
        idinfo = id_token.verify_oauth2_token(
            id_token_str, google_requests.Request(), Settings.GOOGLE_OAUTH2_CLIENT_ID
        )

        if idinfo["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
            raise ValueError("Wrong issuer.")

        return {
            "google_id": idinfo["sub"],
            "email": idinfo["email"],
            "name": idinfo.get("name", ""),
            "picture": idinfo.get("picture", ""),
            "email_verified": idinfo.get("email_verified", False),
        }

    except Exception as e:
        logger.error(f"Error verifying token: {e}")
        return None


# ------------------------------------------------------------
# 4️⃣ Create or Retrieve User from Prisma
# ------------------------------------------------------------
async def get_or_create_google_user(user_info, token_data):
    """Find or create a Google-authenticated user using Prisma."""
    try:
        existing_user = await prisma.prisma.user.find_unique(
            where={"email": user_info["email"]}
        )
        if existing_user:
            # Update Google tokens if available
            await prisma.prisma.user.update(
                where={"email": user_info["email"]},
                data={
                    "google_id": user_info["google_id"],
                    "google_access_token": token_data.get("access_token"),
                    "google_refresh_token": token_data.get("refresh_token"),
                    "google_token_expires_at": datetime.utcnow()
                    + timedelta(seconds=token_data.get("expires_in", 3600)),
                },
            )
            return existing_user, False

        new_user = await prisma.prisma.user.create(
            data={
                "name": user_info["name"],
                "email": user_info["email"],
                "google_id": user_info["google_id"],
                "google_access_token": token_data.get("access_token"),
                "google_refresh_token": token_data.get("refresh_token"),
                "google_token_expires_at": datetime.utcnow()
                + timedelta(seconds=token_data.get("expires_in", 3600)),
            }
        )
        return new_user, True

    except Exception as e:
        logger.error(f"Error creating or fetching user: {e}")
        raise HTTPException(status_code=500, detail="Failed to create or fetch user")
