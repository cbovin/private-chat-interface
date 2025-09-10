"""
Security utilities for JWT tokens, password hashing, and 2FA.
"""
import os
from datetime import datetime, timedelta, UTC
from typing import Optional
from uuid import UUID

import jwt
import pyotp
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from passlib.context import CryptContext

from src.core.config import settings


# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def generate_rsa_keys():
    """Generate RSA key pair for JWT signing."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    return private_pem, public_pem


def load_private_key() -> bytes:
    """Load private key from file."""
    if not os.path.exists(settings.jwt_private_key_path):
        # Generate keys if they don't exist
        private_pem, public_pem = generate_rsa_keys()

        os.makedirs(os.path.dirname(settings.jwt_private_key_path), exist_ok=True)
        with open(settings.jwt_private_key_path, "wb") as f:
            f.write(private_pem)

        with open(settings.jwt_public_key_path, "wb") as f:
            f.write(public_pem)

    with open(settings.jwt_private_key_path, "rb") as f:
        return f.read()


def load_public_key() -> bytes:
    """Load public key from file."""
    if not os.path.exists(settings.jwt_public_key_path):
        load_private_key()  # This will generate both keys if needed

    with open(settings.jwt_public_key_path, "rb") as f:
        return f.read()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(
        to_encode,
        load_private_key(),
        algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """Create JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(
        to_encode,
        load_private_key(),
        algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> Optional[dict]:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(
            token,
            load_public_key(),
            algorithms=[settings.jwt_algorithm]
        )
        if payload.get("type") != token_type:
            return None
        return payload
    except jwt.PyJWTError:
        return None


def generate_totp_secret() -> str:
    """Generate TOTP secret."""
    return pyotp.random_base32()


def get_totp_uri(secret: str, email: str, issuer: str = "Private Chat") -> str:
    """Generate TOTP provisioning URI."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=issuer)


def verify_totp_code(secret: str, code: str) -> bool:
    """Verify TOTP code."""
    totp = pyotp.TOTP(secret)
    return totp.verify(code)


def create_token_pair(user_id: UUID, email: str) -> dict:
    """Create access and refresh token pair."""
    token_data = {"sub": str(user_id), "email": email}

    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }
