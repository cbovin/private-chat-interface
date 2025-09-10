"""
Pydantic schemas for User model.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str


class UserUpdate(BaseModel):
    """Schema for updating user information."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: Optional[bool] = None
    tos_accepted: Optional[bool] = None


class UserResponse(UserBase):
    """Schema for user response."""
    id: UUID
    role: str
    is_active: bool
    is_first_login: bool
    tos_accepted: bool
    twofa_enabled: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Schema for token response."""
    access_token: str
    refresh_token: str
    token_type: str


class TokenData(BaseModel):
    """Schema for token data."""
    sub: str
    email: str


class TwoFASetupResponse(BaseModel):
    """Schema for 2FA setup response."""
    secret: str
    provisioning_uri: str


class TwoFAVerify(BaseModel):
    """Schema for 2FA verification."""
    code: str
