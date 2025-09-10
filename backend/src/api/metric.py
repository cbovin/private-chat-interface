"""
Metrics API endpoints.
"""
import psutil
from datetime import datetime, UTC, timedelta
from typing import Dict, Any, List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.core.db import get_db
from src.core.dependencies import get_current_admin_user
from src.model.user import User, UserRole
from src.model.workspace import Workspace
from src.model.chat import Chat, Message


router = APIRouter()


@router.get("/performance")
async def get_performance_metrics() -> Dict[str, Any]:
    """Get system performance metrics."""
    # CPU metrics
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_count = psutil.cpu_count()
    cpu_freq = psutil.cpu_freq()

    # Memory metrics
    memory = psutil.virtual_memory()

    # Disk metrics
    disk = psutil.disk_usage('/')

    # Network metrics
    network = psutil.net_io_counters()

    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "cpu": {
            "percent": cpu_percent,
            "count": cpu_count,
            "frequency_mhz": cpu_freq.current if cpu_freq else None
        },
        "memory": {
            "total_gb": round(memory.total / (1024**3), 2),
            "used_gb": round(memory.used / (1024**3), 2),
            "free_gb": round(memory.free / (1024**3), 2),
            "percent": memory.percent
        },
        "disk": {
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "percent": disk.percent
        },
        "network": {
            "bytes_sent": network.bytes_sent,
            "bytes_recv": network.bytes_recv,
            "packets_sent": network.packets_sent,
            "packets_recv": network.packets_recv
        }
    }


@router.get("/users")
async def get_user_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """Get user-related metrics (admin only)."""
    # User counts
    total_users = db.query(func.count(User.id)).scalar()
    active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar()
    admin_users = db.query(func.count(User.id)).filter(User.role == UserRole.ADMIN).scalar()
    twofa_users = db.query(func.count(User.id)).filter(User.twofa_enabled == True).scalar()

    # Recent user activity (last 24 hours)
    yesterday = datetime.now(UTC) - timedelta(days=1)
    recent_logins = db.query(func.count(User.id)).filter(User.last_login >= yesterday).scalar()

    # User registration trends (last 30 days)
    thirty_days_ago = datetime.now(UTC) - timedelta(days=30)
    new_users_30d = db.query(func.count(User.id)).filter(User.created_at >= thirty_days_ago).scalar()

    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "user_counts": {
            "total": total_users,
            "active": active_users,
            "admin": admin_users,
            "twofa_enabled": twofa_users
        },
        "activity": {
            "recent_logins_24h": recent_logins,
            "new_users_30d": new_users_30d
        },
        "ratios": {
            "active_ratio": round((active_users / total_users * 100), 2) if total_users > 0 else 0,
            "admin_ratio": round((admin_users / total_users * 100), 2) if total_users > 0 else 0,
            "twofa_ratio": round((twofa_users / total_users * 100), 2) if total_users > 0 else 0
        }
    }


@router.get("/workspaces")
async def get_workspace_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """Get workspace-related metrics (admin only)."""
    # Workspace counts
    total_workspaces = db.query(func.count(Workspace.id)).scalar()

    # Recent workspace activity
    thirty_days_ago = datetime.now(UTC) - timedelta(days=30)
    new_workspaces_30d = db.query(func.count(Workspace.id)).filter(
        Workspace.created_at >= thirty_days_ago
    ).scalar()

    # Average workspaces per user
    total_users = db.query(func.count(User.id)).scalar()
    avg_workspaces_per_user = round(total_workspaces / total_users, 2) if total_users > 0 else 0

    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "workspace_counts": {
            "total": total_workspaces,
            "new_30d": new_workspaces_30d
        },
        "averages": {
            "workspaces_per_user": avg_workspaces_per_user
        }
    }


@router.get("/chats")
async def get_chat_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """Get chat and messaging metrics (admin only)."""
    # Chat counts
    total_chats = db.query(func.count(Chat.id)).scalar()
    total_messages = db.query(func.count(Message.id)).scalar()

    # Recent activity (last 24 hours)
    yesterday = datetime.now(UTC) - timedelta(hours=24)
    recent_messages_24h = db.query(func.count(Message.id)).filter(
        Message.created_at >= yesterday
    ).scalar()

    # Recent activity (last 7 days)
    seven_days_ago = datetime.now(UTC) - timedelta(days=7)
    recent_messages_7d = db.query(func.count(Message.id)).filter(
        Message.created_at >= seven_days_ago
    ).scalar()

    # Average messages per chat
    avg_messages_per_chat = round(total_messages / total_chats, 2) if total_chats > 0 else 0

    # Most active users (by message count)
    from sqlalchemy import desc
    active_users = (
        db.query(
            User.email,
            func.count(Message.id).label('message_count')
        )
        .join(Message, User.id == Message.sender_id)
        .group_by(User.id, User.email)
        .order_by(desc('message_count'))
        .limit(10)
        .all()
    )

    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "chat_counts": {
            "total_chats": total_chats,
            "total_messages": total_messages
        },
        "activity": {
            "messages_24h": recent_messages_24h,
            "messages_7d": recent_messages_7d
        },
        "averages": {
            "messages_per_chat": avg_messages_per_chat
        },
        "top_users": [
            {"email": user.email, "messages": count}
            for user, count in active_users
        ]
    }


@router.get("/tokens")
async def get_token_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """Get token usage metrics (admin only)."""
    # This is a placeholder for token usage tracking
    # In a real implementation, you would track token usage per request
    # and store it in a metrics table

    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "message": "Token usage tracking not yet implemented",
        "placeholder_data": {
            "total_tokens_used": 0,
            "tokens_remaining": 1000000,  # Example quota
            "usage_by_provider": {},
            "usage_by_workspace": {}
        }
    }


@router.get("/summary")
async def get_metrics_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """Get comprehensive metrics summary (admin only)."""
    # Get all metrics in one call
    user_metrics = await get_user_metrics(db, current_user)
    workspace_metrics = await get_workspace_metrics(db, current_user)
    chat_metrics = await get_chat_metrics(db, current_user)
    performance_metrics = await get_performance_metrics()

    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "summary": {
            "users": user_metrics["user_counts"],
            "workspaces": workspace_metrics["workspace_counts"],
            "chats": chat_metrics["chat_counts"],
            "system_health": {
                "cpu_percent": performance_metrics["cpu"]["percent"],
                "memory_percent": performance_metrics["memory"]["percent"],
                "disk_percent": performance_metrics["disk"]["percent"]
            }
        },
        "details": {
            "users": user_metrics,
            "workspaces": workspace_metrics,
            "chats": chat_metrics,
            "performance": performance_metrics
        }
    }
