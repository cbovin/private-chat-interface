"""
Health check API endpoints.
"""
import time
import psutil
from datetime import datetime, UTC
from typing import Dict, Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.core.db import get_db
from src.core.dependencies import get_current_admin_user
from src.services.storage import StorageService
from src.services.inference_provider import inference_service


router = APIRouter()


@router.get("/")
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "service": "Private Chat Interface API"
    }


@router.get("/detailed")
async def detailed_health_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Detailed health check with system information."""
    # Database health
    db_healthy = True
    try:
        db.execute("SELECT 1")
    except Exception:
        db_healthy = False

    # System metrics
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    # Storage health
    storage_healthy = True
    try:
        storage_service = StorageService()
        # Simple check - try to list objects (will fail gracefully if bucket doesn't exist)
        storage_service.list_files("", recursive=False)
    except Exception:
        storage_healthy = False

    # Inference providers health
    inference_healthy = len(inference_service.get_available_providers()) > 0

    overall_healthy = all([
        db_healthy,
        storage_healthy,
        inference_healthy,
        cpu_percent < 90,  # CPU usage under 90%
        memory.percent < 90  # Memory usage under 90%
    ])

    return {
        "status": "healthy" if overall_healthy else "unhealthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "checks": {
            "database": {
                "status": "healthy" if db_healthy else "unhealthy",
                "details": "Database connection is working" if db_healthy else "Database connection failed"
            },
            "storage": {
                "status": "healthy" if storage_healthy else "unhealthy",
                "details": "MinIO storage is accessible" if storage_healthy else "MinIO storage is not accessible"
            },
            "inference": {
                "status": "healthy" if inference_healthy else "unhealthy",
                "details": f"{len(inference_service.get_available_providers())} providers available" if inference_healthy else "No inference providers available"
            }
        },
        "system": {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_used_gb": round(memory.used / (1024**3), 2),
            "memory_total_gb": round(memory.total / (1024**3), 2),
            "disk_percent": disk.percent,
            "disk_used_gb": round(disk.used / (1024**3), 2),
            "disk_total_gb": round(disk.total / (1024**3), 2)
        }
    }


@router.get("/database")
async def database_health_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Database-specific health check."""
    start_time = time.time()

    try:
        # Test basic query
        result = db.execute("SELECT 1 as test").fetchone()
        query_time = time.time() - start_time

        # Get some basic stats
        user_count = db.query("SELECT COUNT(*) FROM user").scalar()
        workspace_count = db.query("SELECT COUNT(*) FROM workspace").scalar()
        chat_count = db.query("SELECT COUNT(*) FROM chat").scalar()

        return {
            "status": "healthy",
            "timestamp": datetime.now(UTC).isoformat(),
            "response_time_ms": round(query_time * 1000, 2),
            "stats": {
                "users": user_count,
                "workspaces": workspace_count,
                "chats": chat_count
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.now(UTC).isoformat(),
            "error": str(e)
        }


@router.get("/storage")
async def storage_health_check() -> Dict[str, Any]:
    """Storage-specific health check."""
    start_time = time.time()

    try:
        storage_service = StorageService()
        files = storage_service.list_files("", recursive=False)
        response_time = time.time() - start_time

        return {
            "status": "healthy",
            "timestamp": datetime.now(UTC).isoformat(),
            "response_time_ms": round(response_time * 1000, 2),
            "bucket": storage_service.bucket_name,
            "files_count": len(files)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.now(UTC).isoformat(),
            "error": str(e)
        }


@router.get("/inference")
async def inference_health_check() -> Dict[str, Any]:
    """Inference providers health check."""
    providers = inference_service.get_available_providers()
    provider_details = []

    for provider_name in providers:
        info = inference_service.get_provider_info(provider_name)
        provider_details.append({
            "name": provider_name,
            "type": info["type"] if info else "unknown",
            "models": info["models"] if info else []
        })

    return {
        "status": "healthy" if providers else "unhealthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "providers": provider_details,
        "total_providers": len(providers)
    }
