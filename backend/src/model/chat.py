"""
Chat and Message models.
"""
from datetime import datetime, UTC
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import JSON
from sqlmodel import Field, SQLModel, Relationship


class Chat(SQLModel, table=True):
    """Chat model for conversations that can be standalone or within workspaces."""

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    title: str = Field(nullable=False)
    workspace_id: Optional[UUID] = Field(foreign_key="workspace.id", nullable=True, default=None)
    created_by: UUID = Field(foreign_key="user.id", nullable=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)

    # Relationships
    workspace: Optional["Workspace"] = Relationship(back_populates="chats")
    creator: "User" = Relationship(back_populates="created_chats")
    messages: list["Message"] = Relationship(back_populates="chat")


class Message(SQLModel, table=True):
    """Message model for chat messages."""

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    chat_id: UUID = Field(foreign_key="chat.id", nullable=False)
    sender_id: Optional[UUID] = Field(foreign_key="user.id", nullable=True, default=None)
    content: str = Field(nullable=False)  # Using TEXT type in MySQL
    attachments: Optional[List[str]] = Field(default_factory=list, sa_type=JSON)  # MinIO URLs
    is_ai_response: bool = Field(default=False, nullable=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)

    # Relationships
    chat: Chat = Relationship(back_populates="messages")
    sender: Optional["User"] = Relationship(back_populates="sent_messages")
