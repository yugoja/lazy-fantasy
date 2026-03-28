from typing import Optional
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    """Schema for user registration."""
    username: str
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Schema for user response (excludes password)."""
    id: int
    username: str
    email: str
    display_name: Optional[str] = None

    model_config = {"from_attributes": True}


class Token(BaseModel):
    """Schema for JWT token response."""
    access_token: str
    token_type: str = "bearer"
    display_name: Optional[str] = None


class TokenData(BaseModel):
    """Schema for decoded token data."""
    user_id: int | None = None


class GoogleAuthRequest(BaseModel):
    """Schema for Google SSO login."""
    credential: str


class GoogleAuthResponse(BaseModel):
    """Schema for Google SSO response (JWT + username for frontend login)."""
    access_token: str
    token_type: str = "bearer"
    username: str
    display_name: Optional[str] = None


class ProfileUpdate(BaseModel):
    """Schema for updating user profile."""
    display_name: str
