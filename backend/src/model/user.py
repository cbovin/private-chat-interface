"""
User model and related enums.
"""
import enum
from datetime import datetime, UTC
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel, Relationship

from src.model.chat import Message, Chat
from src.model.workspace import WorkspaceUser, Workspace


class UserRole(str, enum.Enum):
    """User role enumeration."""
    USER = "USER"
    ADMIN = "ADMIN"


class User(SQLModel, table=True):
    """User model with authentication and profile information."""

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    email: str = Field(index=True, unique=True, nullable=False)
    hashed_password: str = Field(nullable=False)
    first_name: Optional[str] = Field(default=None)
    last_name: Optional[str] = Field(default=None)
    role: UserRole = Field(default=UserRole.USER)
    is_active: bool = Field(default=True)
    is_first_login: bool = Field(default=True)
    tos_accepted: bool = Field(default=False)
    twofa_enabled: bool = Field(default=False)
    twofa_secret: Optional[str] = Field(default=None)
    last_login: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)

    # Relationships
    created_workspaces: list["Workspace"] = Relationship(back_populates="creator")
    workspace_memberships: list["WorkspaceUser"] = Relationship(back_populates="user")
    created_chats: list["Chat"] = Relationship(back_populates="creator")
    sent_messages: list["Message"] = Relationship(back_populates="sender")
