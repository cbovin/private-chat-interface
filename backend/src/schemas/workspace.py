"""
Pydantic schemas for Workspace models.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class WorkspaceBase(BaseModel):
    """Base workspace schema."""
    name: str


class WorkspaceCreate(WorkspaceBase):
    """Schema for creating a new workspace."""
    pass


class WorkspaceUpdate(BaseModel):
    """Schema for updating workspace information."""
    name: Optional[str] = None


class WorkspaceResponse(WorkspaceBase):
    """Schema for workspace response."""
    id: UUID
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkspaceUserBase(BaseModel):
    """Base workspace user schema."""
    workspace_id: UUID
    user_id: UUID
    role: str


class WorkspaceUserCreate(BaseModel):
    """Schema for adding user to workspace."""
    user_id: UUID
    role: str = "MEMBER"


class WorkspaceUserResponse(WorkspaceUserBase):
    """Schema for workspace user response."""
    joined_at: datetime

    class Config:
        from_attributes = True


class WorkspaceWithUsers(WorkspaceResponse):
    """Schema for workspace with users."""
    users: List[WorkspaceUserResponse] = []

    class Config:
        from_attributes = True


class WorkspaceInvite(BaseModel):
    """Schema for inviting user to workspace."""
    email: str
    role: str = "MEMBER"
