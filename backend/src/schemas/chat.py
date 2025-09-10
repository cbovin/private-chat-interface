"""
Pydantic schemas for Chat and Message models.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class ChatBase(BaseModel):
    """Base chat schema."""
    title: str


class ChatCreate(ChatBase):
    """Schema for creating a new chat."""
    pass


class ChatUpdate(BaseModel):
    """Schema for updating chat information."""
    title: Optional[str] = None


class ChatResponse(ChatBase):
    """Schema for chat response."""
    id: UUID
    workspace_id: Optional[UUID] = None
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MessageBase(BaseModel):
    """Base message schema."""
    content: str
    attachments: Optional[List[str]] = None


class MessageCreate(MessageBase):
    """Schema for creating a new message."""
    pass


class MessageResponse(MessageBase):
    """Schema for message response."""
    id: UUID
    chat_id: UUID
    sender_id: Optional[UUID] = None
    is_ai_response: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class ChatWithMessages(ChatResponse):
    """Schema for chat with messages."""
    messages: List[MessageResponse] = []

    class Config:
        from_attributes = True


class PaginatedMessages(BaseModel):
    """Schema for paginated messages."""
    messages: List[MessageResponse]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool
