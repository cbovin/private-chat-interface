"""
Authentication API endpoints.
"""
from datetime import datetime, UTC
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.core.db import get_db
from src.core.dependencies import get_current_user
from src.core.security import (
    create_token_pair,
    generate_totp_secret,
    get_password_hash,
    get_totp_uri,
    verify_password,
    verify_token,
    verify_totp_code
)
from src.model.user import User, UserRole
from src.schemas.user import (
    TokenResponse,
    TwoFASetupResponse,
    TwoFAVerify,
    UserCreate,
    UserLogin,
    UserResponse
)


router = APIRouter()


@router.post("/setup", response_model=UserResponse)
async def setup_first_admin(
    user_data: UserCreate,
    db: Session = Depends(get_db)
) -> UserResponse:
    """Setup first admin user. Only works when no users exist."""
    # Check if any users exist
    user_count = db.query(User).count()
    if user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Setup already completed"
        )

    # Create admin user
    hashed_password = get_password_hash(user_data.password)
    user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        role=UserRole.ADMIN,
        is_first_login=True,
        tos_accepted=False,
        twofa_enabled=False
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return UserResponse.from_orm(user)


@router.post("/login", response_model=dict)
async def login(
    user_credentials: UserLogin,
    db: Session = Depends(get_db)
) -> dict:
    """Login user and return tokens or 2FA requirement."""
    user = db.query(User).filter(User.email == user_credentials.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    if not verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    # Update last login
    user.last_login = datetime.now(UTC)
    db.commit()

    if user.twofa_enabled:
        return {
            "requires_2fa": True,
            "user_id": str(user.id),
            "message": "2FA verification required"
        }

    # Create tokens
    tokens = create_token_pair(user.id, user.email)

    return {
        "requires_2fa": False,
        "tokens": tokens,
        "user": UserResponse.from_orm(user)
    }


@router.post("/login/2fa", response_model=dict)
async def login_2fa(
    user_id: str,
    twofa_data: TwoFAVerify,
    db: Session = Depends(get_db)
) -> dict:
    """Complete login with 2FA verification."""
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID"
        )

    user = db.query(User).filter(User.id == user_uuid).first()
    if not user or not user.twofa_enabled or not user.twofa_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid 2FA verification"
        )

    if not verify_totp_code(user.twofa_secret, twofa_data.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid 2FA code"
        )

    # Create tokens
    tokens = create_token_pair(user.id, user.email)

    return {
        "tokens": tokens,
        "user": UserResponse.from_orm(user)
    }


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db)
) -> TokenResponse:
    """Refresh access token using refresh token."""
    payload = verify_token(refresh_token, "refresh")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    try:
        user_id = UUID(payload["sub"])
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token data"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    # Create new token pair
    tokens = create_token_pair(user.id, user.email)
    return TokenResponse(**tokens)


@router.post("/2fa/setup", response_model=TwoFASetupResponse)
async def setup_2fa(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> TwoFASetupResponse:
    """Setup 2FA for current user."""
    if current_user.twofa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA already enabled"
        )

    secret = generate_totp_secret()
    provisioning_uri = get_totp_uri(secret, current_user.email)

    # Store secret temporarily (user needs to verify before enabling)
    current_user.twofa_secret = secret
    db.commit()

    return TwoFASetupResponse(
        secret=secret,
        provisioning_uri=provisioning_uri
    )


@router.post("/2fa/verify")
async def verify_2fa_setup(
    twofa_data: TwoFAVerify,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify 2FA setup and enable 2FA."""
    if current_user.twofa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA already enabled"
        )

    if not current_user.twofa_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA setup not initiated"
        )

    if not verify_totp_code(current_user.twofa_secret, twofa_data.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid 2FA code"
        )

    # Enable 2FA
    current_user.twofa_enabled = True
    db.commit()

    return {"message": "2FA enabled successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    """Get current user information."""
    return UserResponse.from_orm(current_user)
