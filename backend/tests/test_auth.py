"""
Authentication endpoint tests.
"""
import pytest
from sqlalchemy.orm import Session

from src.model.user import User, UserRole
from src.schemas.user import UserCreate


def test_setup_first_admin(client, db_session: Session):
    """Test first admin setup."""
    # Ensure no users exist
    assert db_session.query(User).count() == 0

    user_data = UserCreate(
        email="admin@example.com",
        password="securepassword123",
        first_name="Admin",
        last_name="User"
    )

    response = client.post("/auth/setup", json=user_data.dict())
    assert response.status_code == 200

    data = response.json()
    assert data["email"] == user_data.email
    assert data["role"] == "ADMIN"
    assert data["is_first_login"] is True

    # Verify user was created in database
    user = db_session.query(User).filter(User.email == user_data.email).first()
    assert user is not None
    assert user.role == UserRole.ADMIN


def test_setup_admin_twice_fails(client, db_session: Session):
    """Test that setup can only be called once."""
    # First setup
    user_data = UserCreate(
        email="admin@example.com",
        password="securepassword123"
    )

    response = client.post("/auth/setup", json=user_data.dict())
    assert response.status_code == 200

    # Second setup should fail
    user_data2 = UserCreate(
        email="admin2@example.com",
        password="anotherpassword123"
    )

    response = client.post("/auth/setup", json=user_data2.dict())
    assert response.status_code == 400
    assert "Setup already completed" in response.json()["detail"]


def test_login_success(client, db_session: Session):
    """Test successful login."""
    # Create a user first
    from src.core.security import get_password_hash
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpassword"),
        role=UserRole.USER
    )
    db_session.add(user)
    db_session.commit()

    login_data = {
        "email": "test@example.com",
        "password": "testpassword"
    }

    response = client.post("/auth/login", json=login_data)
    assert response.status_code == 200

    data = response.json()
    assert "tokens" in data
    assert "user" in data
    assert data["user"]["email"] == user.email


def test_login_wrong_password(client, db_session: Session):
    """Test login with wrong password."""
    # Create a user first
    from src.core.security import get_password_hash
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpassword"),
        role=UserRole.USER
    )
    db_session.add(user)
    db_session.commit()

    login_data = {
        "email": "test@example.com",
        "password": "wrongpassword"
    }

    response = client.post("/auth/login", json=login_data)
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


def test_login_nonexistent_user(client):
    """Test login with nonexistent user."""
    login_data = {
        "email": "nonexistent@example.com",
        "password": "password"
    }

    response = client.post("/auth/login", json=login_data)
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


def test_get_current_user_unauthenticated(client):
    """Test accessing protected endpoint without authentication."""
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_get_current_user_authenticated(client, db_session: Session):
    """Test accessing protected endpoint with authentication."""
    # Create and login user
    from src.core.security import get_password_hash
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpassword"),
        role=UserRole.USER
    )
    db_session.add(user)
    db_session.commit()

    login_data = {
        "email": "test@example.com",
        "password": "testpassword"
    }

    login_response = client.post("/auth/login", json=login_data)
    tokens = login_response.json()["tokens"]

    # Access protected endpoint
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    response = client.get("/auth/me", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == user.email
