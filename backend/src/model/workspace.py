"""
Workspace and WorkspaceUser models.
"""
import enum
from datetime import datetime, UTC
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel, Relationship


class WorkspaceRole(str, enum.Enum):
    """Workspace role enumeration."""
    OWNER = "OWNER"
    MEMBER = "MEMBER"
    GUEST = "GUEST"


class Workspace(SQLModel, table=True):
    """Workspace model for organizing chats and users."""

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    name: str = Field(nullable=False)
    created_by: UUID = Field(foreign_key="user.id", nullable=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)

    # Relationships
    creator: "User" = Relationship(back_populates="created_workspaces")
    workspace_users: list["WorkspaceUser"] = Relationship(back_populates="workspace")
    chats: list[Optional["Chat"]] = Relationship(back_populates="workspace")


class WorkspaceUser(SQLModel, table=True):
    """Many-to-many relationship between users and workspaces with roles."""

    workspace_id: UUID = Field(foreign_key="workspace.id", primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", primary_key=True)
    role: WorkspaceRole = Field(default=WorkspaceRole.MEMBER)
    joined_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)

    # Relationships
    workspace: Workspace = Relationship(back_populates="workspace_users")
    user: "User" = Relationship(back_populates="workspace_memberships")
