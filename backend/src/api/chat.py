"""
Chat and messaging API endpoints.
"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session, joinedload

from src.core.db import get_db
from src.core.dependencies import get_current_user
from src.model.user import User
from src.model.workspace import Workspace, WorkspaceUser, WorkspaceRole
from src.model.chat import Chat, Message
from src.schemas.chat import (
    ChatCreate,
    ChatResponse,
    MessageCreate,
    MessageResponse,
    ChatWithMessages,
    PaginatedMessages
)
from src.services.storage import StorageService
from src.services.inference_provider import inference_service, InferenceRequest


router = APIRouter()


def check_workspace_access(
    workspace: Workspace,
    user: User,
    required_role: WorkspaceRole = WorkspaceRole.GUEST
) -> bool:
    """Check if user has access to workspace with required role."""
    workspace_user = None
    for wu in workspace.workspace_users:
        if wu.user_id == user.id:
            workspace_user = wu
            break

    if not workspace_user:
        return False

    role_hierarchy = {
        WorkspaceRole.OWNER: 3,
        WorkspaceRole.MEMBER: 2,
        WorkspaceRole.GUEST: 1
    }

    user_level = role_hierarchy.get(workspace_user.role, 0)
    required_level = role_hierarchy.get(required_role, 0)

    return user_level >= required_level


@router.get("/{workspace_id}/chats/history", response_model=List[ChatResponse])
async def get_workspace_chats(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[ChatResponse]:
    """Get all chats in a workspace."""
    try:
        workspace_uuid = UUID(workspace_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid workspace ID"
        )

    workspace = (
        db.query(Workspace)
        .options(joinedload(Workspace.workspace_users))
        .filter(Workspace.id == workspace_uuid)
        .first()
    )

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )

    if not check_workspace_access(workspace, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    chats = (
        db.query(Chat)
        .filter(Chat.workspace_id == workspace.id)
        .options(joinedload(Chat.creator))
        .all()
    )

    return [ChatResponse.from_orm(chat) for chat in chats]


@router.post("/{workspace_id}/chat", response_model=ChatResponse)
async def create_chat(
    workspace_id: str,
    chat_data: ChatCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ChatResponse:
    """Create a new chat in workspace."""
    try:
        workspace_uuid = UUID(workspace_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid workspace ID"
        )

    workspace = (
        db.query(Workspace)
        .options(joinedload(Workspace.workspace_users))
        .filter(Workspace.id == workspace_uuid)
        .first()
    )

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )

    if not check_workspace_access(workspace, current_user, WorkspaceRole.MEMBER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to create chats"
        )

    chat = Chat(
        title=chat_data.title,
        workspace_id=workspace.id,
        created_by=current_user.id
    )

    db.add(chat)
    db.commit()
    db.refresh(chat)

    return ChatResponse.from_orm(chat)


@router.get("/{workspace_id}/chat/{chat_id}", response_model=ChatWithMessages)
async def get_chat(
    workspace_id: str,
    chat_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ChatWithMessages:
    """Get chat with messages."""
    try:
        workspace_uuid = UUID(workspace_id)
        chat_uuid = UUID(chat_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID format"
        )

    workspace = (
        db.query(Workspace)
        .options(joinedload(Workspace.workspace_users))
        .filter(Workspace.id == workspace_uuid)
        .first()
    )

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )

    if not check_workspace_access(workspace, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    chat = (
        db.query(Chat)
        .options(
            joinedload(Chat.messages).joinedload(Message.sender),
            joinedload(Chat.creator)
        )
        .filter(
            Chat.id == chat_uuid,
            Chat.workspace_id == workspace.id
        )
        .first()
    )

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )

    return ChatWithMessages.from_orm(chat)


@router.get("/{workspace_id}/chat/{chat_id}/messages", response_model=PaginatedMessages)
async def get_chat_messages(
    workspace_id: str,
    chat_id: str,
    page: int = 1,
    page_size: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> PaginatedMessages:
    """Get paginated messages for a chat."""
    try:
        workspace_uuid = UUID(workspace_id)
        chat_uuid = UUID(chat_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID format"
        )

    workspace = (
        db.query(Workspace)
        .options(joinedload(Workspace.workspace_users))
        .filter(Workspace.id == workspace_uuid)
        .first()
    )

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )

    if not check_workspace_access(workspace, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    # Verify chat exists in workspace
    chat = (
        db.query(Chat)
        .filter(
            Chat.id == chat_uuid,
            Chat.workspace_id == workspace.id
        )
        .first()
    )

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )

    # Get total count
    total = (
        db.query(Message)
        .filter(Message.chat_id == chat.id)
        .count()
    )

    # Get paginated messages
    messages = (
        db.query(Message)
        .options(joinedload(Message.sender))
        .filter(Message.chat_id == chat.id)
        .order_by(Message.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # Reverse to get chronological order
    messages.reverse()

    return PaginatedMessages(
        messages=[MessageResponse.from_orm(msg) for msg in messages],
        total=total,
        page=page,
        page_size=page_size,
        has_next=(page * page_size) < total,
        has_prev=page > 1
    )


@router.post("/{workspace_id}/chat/{chat_id}/message", response_model=MessageResponse)
async def send_message(
    workspace_id: str,
    chat_id: str,
    message_data: MessageCreate,
    files: List[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> MessageResponse:
    """Send a message to a chat and get LLM response."""
    try:
        workspace_uuid = UUID(workspace_id)
        chat_uuid = UUID(chat_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID format"
        )

    workspace = (
        db.query(Workspace)
        .options(joinedload(Workspace.workspace_users))
        .filter(Workspace.id == workspace_uuid)
        .first()
    )

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )

    if not check_workspace_access(workspace, current_user, WorkspaceRole.MEMBER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to send messages"
        )

    # Verify chat exists in workspace
    chat = (
        db.query(Chat)
        .filter(
            Chat.id == chat_uuid,
            Chat.workspace_id == workspace.id
        )
        .first()
    )

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )

    # Handle file attachments
    attachment_urls = []
    if files:
        storage_service = StorageService()
        for file in files:
            if file.filename:
                file_url = await storage_service.upload_file(
                    file,
                    f"workspace_{workspace.id}/chat_{chat.id}"
                )
                attachment_urls.append(file_url)

    # Create user message
    user_message = Message(
        chat_id=chat.id,
        sender_id=current_user.id,
        content=message_data.content,
        attachments=attachment_urls if attachment_urls else None
    )

    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    # Get conversation history for context
    recent_messages = (
        db.query(Message)
        .filter(Message.chat_id == chat.id)
        .order_by(Message.created_at.desc())
        .limit(20)  # Get last 20 messages for context
        .all()
    )

    # Reverse to get chronological order
    recent_messages.reverse()

    # Prepare messages for LLM
    conversation_messages = []
    for msg in recent_messages:
        role = "assistant" if msg.sender_id != current_user.id else "user"
        conversation_messages.append({
            "role": role,
            "content": msg.content
        })

    # Add the new user message if not already included
    if not conversation_messages or conversation_messages[-1]["role"] != "user":
        conversation_messages.append({
            "role": "user",
            "content": message_data.content
        })

    try:
        # Generate LLM response
        inference_request = InferenceRequest(
            messages=conversation_messages,
            temperature=0.7,
            max_tokens=1000
        )

        inference_response = await inference_service.generate(
            inference_request,
            workspace_id=str(workspace.id)
        )

        # Create LLM response message
        llm_message = Message(
            chat_id=chat.id,
            sender_id=None,  # LLM doesn't have a user ID
            content=inference_response.content,
            is_ai_response=True  # Assuming we add this field to distinguish AI responses
        )

        db.add(llm_message)
        db.commit()
        db.refresh(llm_message)

    except Exception as e:
        # Log the error but don't fail the request
        print(f"LLM inference failed: {str(e)}")
        # Continue without LLM response

    return MessageResponse.from_orm(user_message)


@router.delete("/{workspace_id}/chat/{chat_id}")
async def delete_chat(
    workspace_id: str,
    chat_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a chat (owner only)."""
    try:
        workspace_uuid = UUID(workspace_id)
        chat_uuid = UUID(chat_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID format"
        )

    workspace = (
        db.query(Workspace)
        .options(joinedload(Workspace.workspace_users))
        .filter(Workspace.id == workspace_uuid)
        .first()
    )

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )

    if not check_workspace_access(workspace, current_user, WorkspaceRole.OWNER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only workspace owners can delete chats"
        )

    chat = (
        db.query(Chat)
        .filter(
            Chat.id == chat_uuid,
            Chat.workspace_id == workspace.id
        )
        .first()
    )

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )

    db.delete(chat)
    db.commit()

    return {"message": "Chat deleted successfully"}


# Standalone chat endpoints (not bound to workspaces)

@router.post("/standalone", response_model=ChatResponse)
async def create_standalone_chat(
    chat_data: ChatCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ChatResponse:
    """Create a new standalone chat (not bound to any workspace)."""
    chat = Chat(
        title=chat_data.title,
        workspace_id=None,  # No workspace
        created_by=current_user.id
    )

    db.add(chat)
    db.commit()
    db.refresh(chat)

    return ChatResponse.from_orm(chat)


@router.get("/standalone", response_model=List[ChatResponse])
async def get_standalone_chats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[ChatResponse]:
    """Get all standalone chats for the current user."""
    chats = (
        db.query(Chat)
        .filter(
            Chat.created_by == current_user.id,
            Chat.workspace_id.is_(None)  # Only standalone chats
        )
        .options(joinedload(Chat.creator))
        .all()
    )

    return [ChatResponse.from_orm(chat) for chat in chats]


@router.get("/standalone/{chat_id}", response_model=ChatWithMessages)
async def get_standalone_chat(
    chat_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ChatWithMessages:
    """Get a standalone chat with messages."""
    try:
        chat_uuid = UUID(chat_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid chat ID"
        )

    chat = (
        db.query(Chat)
        .options(
            joinedload(Chat.messages).joinedload(Message.sender),
            joinedload(Chat.creator)
        )
        .filter(
            Chat.id == chat_uuid,
            Chat.created_by == current_user.id,
            Chat.workspace_id.is_(None)  # Only standalone chats
        )
        .first()
    )

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Standalone chat not found"
        )

    return ChatWithMessages.from_orm(chat)


@router.post("/standalone/{chat_id}/attach/{workspace_id}")
async def attach_chat_to_workspace(
    chat_id: str,
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Attach a standalone chat to a workspace."""
    try:
        chat_uuid = UUID(chat_id)
        workspace_uuid = UUID(workspace_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID format"
        )

    # Get the standalone chat
    chat = (
        db.query(Chat)
        .filter(
            Chat.id == chat_uuid,
            Chat.created_by == current_user.id,
            Chat.workspace_id.is_(None)  # Must be standalone
        )
        .first()
    )

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Standalone chat not found"
        )

    # Get the workspace and check access
    workspace = (
        db.query(Workspace)
        .options(joinedload(Workspace.workspace_users))
        .filter(Workspace.id == workspace_uuid)
        .first()
    )

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )

    if not check_workspace_access(workspace, current_user, WorkspaceRole.MEMBER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to attach chats to this workspace"
        )

    # Attach chat to workspace
    chat.workspace_id = workspace.id
    db.commit()

    return {"message": "Chat attached to workspace successfully"}


@router.get("/standalone/{chat_id}/messages", response_model=PaginatedMessages)
async def get_standalone_chat_messages(
    chat_id: str,
    page: int = 1,
    page_size: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> PaginatedMessages:
    """Get paginated messages for a standalone chat."""
    try:
        chat_uuid = UUID(chat_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid chat ID"
        )

    # Verify chat exists and is standalone
    chat = (
        db.query(Chat)
        .filter(
            Chat.id == chat_uuid,
            Chat.created_by == current_user.id,
            Chat.workspace_id.is_(None)  # Only standalone chats
        )
        .first()
    )

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Standalone chat not found"
        )

    # Get total count
    total = (
        db.query(Message)
        .filter(Message.chat_id == chat.id)
        .count()
    )

    # Get paginated messages
    messages = (
        db.query(Message)
        .options(joinedload(Message.sender))
        .filter(Message.chat_id == chat.id)
        .order_by(Message.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # Reverse to get chronological order
    messages.reverse()

    return PaginatedMessages(
        messages=[MessageResponse.from_orm(msg) for msg in messages],
        total=total,
        page=page,
        page_size=page_size,
        has_next=(page * page_size) < total,
        has_prev=page > 1
    )


@router.post("/standalone/{chat_id}/message", response_model=MessageResponse)
async def send_message_to_standalone_chat(
    chat_id: str,
    message_data: MessageCreate,
    files: List[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> MessageResponse:
    """Send a message to a standalone chat."""
    try:
        chat_uuid = UUID(chat_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid chat ID"
        )

    # Verify chat exists and is standalone
    chat = (
        db.query(Chat)
        .filter(
            Chat.id == chat_uuid,
            Chat.created_by == current_user.id,
            Chat.workspace_id.is_(None)  # Only standalone chats
        )
        .first()
    )

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Standalone chat not found"
        )

    # Handle file attachments
    attachment_urls = []
    if files:
        storage_service = StorageService()
        for file in files:
            if file.filename:
                file_url = await storage_service.upload_file(
                    file,
                    f"user_{current_user.id}/chat_{chat.id}"
                )
                attachment_urls.append(file_url)

    # Create message
    message = Message(
        chat_id=chat.id,
        sender_id=current_user.id,
        content=message_data.content,
        attachments=attachment_urls if attachment_urls else None
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    return MessageResponse.from_orm(message)


@router.delete("/standalone/{chat_id}")
async def delete_standalone_chat(
    chat_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a standalone chat."""
    try:
        chat_uuid = UUID(chat_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid chat ID"
        )

    chat = (
        db.query(Chat)
        .filter(
            Chat.id == chat_uuid,
            Chat.created_by == current_user.id,
            Chat.workspace_id.is_(None)  # Only standalone chats
        )
        .first()
    )

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Standalone chat not found"
        )

    db.delete(chat)
    db.commit()

    return {"message": "Standalone chat deleted successfully"}
