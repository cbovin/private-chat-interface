"""
Workspace management API endpoints.
"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from src.core.db import get_db
from src.core.dependencies import get_current_user
from src.model.user import User
from src.model.workspace import Workspace, WorkspaceUser, WorkspaceRole
from src.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceResponse,
    WorkspaceUpdate,
    WorkspaceInvite,
    WorkspaceWithUsers
)


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


@router.get("/", response_model=List[WorkspaceResponse])
async def get_user_workspaces(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[WorkspaceResponse]:
    """Get all workspaces for the current user."""
    workspaces = (
        db.query(Workspace)
        .join(WorkspaceUser)
        .filter(WorkspaceUser.user_id == current_user.id)
        .options(joinedload(Workspace.workspace_users))
        .all()
    )

    return [WorkspaceResponse.from_orm(workspace) for workspace in workspaces]


@router.post("/", response_model=WorkspaceResponse)
async def create_workspace(
    workspace_data: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> WorkspaceResponse:
    """Create a new workspace."""
    workspace = Workspace(
        name=workspace_data.name,
        created_by=current_user.id
    )

    db.add(workspace)
    db.commit()
    db.refresh(workspace)

    # Add creator as owner
    workspace_user = WorkspaceUser(
        workspace_id=workspace.id,
        user_id=current_user.id,
        role=WorkspaceRole.OWNER
    )

    db.add(workspace_user)
    db.commit()
    db.refresh(workspace)

    return WorkspaceResponse.from_orm(workspace)


@router.get("/{workspace_id}", response_model=WorkspaceWithUsers)
async def get_workspace(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> WorkspaceWithUsers:
    """Get workspace details."""
    try:
        workspace_uuid = UUID(workspace_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid workspace ID"
        )

    workspace = (
        db.query(Workspace)
        .options(
            joinedload(Workspace.workspace_users).joinedload(WorkspaceUser.user),
            joinedload(Workspace.creator)
        )
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

    return WorkspaceWithUsers.from_orm(workspace)


@router.put("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: str,
    workspace_update: WorkspaceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> WorkspaceResponse:
    """Update workspace (owner only)."""
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

    if not check_workspace_access(workspace, current_user, WorkspaceRole.OWNER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only workspace owners can update workspace"
        )

    # Update workspace fields
    update_data = workspace_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(workspace, field, value)

    db.commit()
    db.refresh(workspace)

    return WorkspaceResponse.from_orm(workspace)


@router.delete("/{workspace_id}")
async def delete_workspace(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete workspace (owner only)."""
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

    if not check_workspace_access(workspace, current_user, WorkspaceRole.OWNER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only workspace owners can delete workspace"
        )

    db.delete(workspace)
    db.commit()

    return {"message": "Workspace deleted successfully"}


@router.post("/{workspace_id}/invite")
async def invite_user_to_workspace(
    workspace_id: str,
    invite_data: WorkspaceInvite,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Invite user to workspace (owner/member only)."""
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
            detail="Not enough permissions to invite users"
        )

    # Find user by email
    user = db.query(User).filter(User.email == invite_data.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check if user is already in workspace
    existing_membership = (
        db.query(WorkspaceUser)
        .filter(
            WorkspaceUser.workspace_id == workspace.id,
            WorkspaceUser.user_id == user.id
        )
        .first()
    )

    if existing_membership:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this workspace"
        )

    # Validate role
    try:
        role = WorkspaceRole(invite_data.role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role"
        )

    # Create workspace membership
    workspace_user = WorkspaceUser(
        workspace_id=workspace.id,
        user_id=user.id,
        role=role
    )

    db.add(workspace_user)
    db.commit()

    return {
        "message": f"User {user.email} invited to workspace with role {role.value}",
        "workspace_user_id": str(workspace_user.workspace_id)
    }


@router.delete("/{workspace_id}/users/{user_id}")
async def remove_user_from_workspace(
    workspace_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove user from workspace (owner only)."""
    try:
        workspace_uuid = UUID(workspace_id)
        user_uuid = UUID(user_id)
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
            detail="Only workspace owners can remove users"
        )

    # Find workspace user
    workspace_user = (
        db.query(WorkspaceUser)
        .filter(
            WorkspaceUser.workspace_id == workspace.id,
            WorkspaceUser.user_id == user_uuid
        )
        .first()
    )

    if not workspace_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not a member of this workspace"
        )

    # Prevent owner from removing themselves if they're the only owner
    if workspace_user.role == WorkspaceRole.OWNER:
        owner_count = sum(
            1 for wu in workspace.workspace_users
            if wu.role == WorkspaceRole.OWNER
        )
        if owner_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the last owner from workspace"
            )

    db.delete(workspace_user)
    db.commit()

    return {"message": "User removed from workspace successfully"}
