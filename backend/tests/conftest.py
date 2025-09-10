"""
Pytest configuration and fixtures.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from src.main import app
from src.core.db import get_db
from src.core.config import settings


# Test database
TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Create test database tables."""
    SQLModel.metadata.create_all(bind=engine)
    yield
    # Cleanup after tests
    SQLModel.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """Test client fixture."""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def db_session():
    """Database session fixture."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
