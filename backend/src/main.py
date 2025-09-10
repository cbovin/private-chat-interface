"""
Main FastAPI application entry point.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from src.api import auth, user, workspace, chat, health, metric
from src.core.config import settings
from src.core.db import create_db_and_tables


def initialize_logging():
    """Initialize logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    # Startup
    initialize_logging()
    create_db_and_tables()
    logging.info("Application startup complete")
    yield
    # Shutdown
    logging.info("Application shutdown complete")


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Private Chat Interface Backend API",
    lifespan=lifespan,
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.trusted_hosts_list:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.trusted_hosts_list,
    )

# Include routers
app.include_router(auth, prefix="/api/auth", tags=["Authentication"])
app.include_router(user, prefix="/api/users", tags=["Users"])
app.include_router(workspace, prefix="/api/workspaces", tags=["Workspaces"])
app.include_router(chat, prefix="/api/chats", tags=["Chats"])
app.include_router(health, prefix="/api/health", tags=["Health"])
app.include_router(metric, prefix="/api/metrics", tags=["Metrics"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Private Chat Interface API", "version": "1.0.0"}
