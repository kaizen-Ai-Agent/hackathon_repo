from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

# -------------------------
# Base Schema
# -------------------------
class UserBase(BaseModel):
    name: str
    email: EmailStr
    google_id: str
    google_access_token: Optional[str] = None
    google_refresh_token: Optional[str] = None
    google_token_expires_at: Optional[datetime] = None

# -------------------------
# For Create (password allowed)
# -------------------------
class UserCreate(UserBase):
    password: Optional[str] = None

# -------------------------
# For Read / Response
# -------------------------
class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    class Config:
        orm_mode = True

# -------------------------
# For Update
# -------------------------
class UserUpdate(BaseModel):
    name: Optional[str] = None
    password: Optional[str] = None
    google_access_token: Optional[str] = None
    google_refresh_token: Optional[str] = None
    google_token_expires_at: Optional[datetime] = None