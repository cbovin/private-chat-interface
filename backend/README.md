# Private Chat Interface Backend

A production-ready FastAPI backend for a private chat interface with JWT authentication, 2FA, workspace management, and MinIO file storage.

## Features

- **Authentication & Security**
  - JWT RS256 tokens (access + refresh)
  - Optional 2FA with TOTP
  - Password hashing with bcrypt
  - Role-based access control (USER, ADMIN)

- **Workspace Management**
  - Multi-workspace support
  - Role-based permissions (OWNER, MEMBER, GUEST)
  - User invitation system

- **Chat & Messaging**
  - Real-time chat functionality
  - File attachments via MinIO
  - Message pagination
  - Chat history

- **File Storage**
  - MinIO integration for file uploads
  - Presigned URLs for secure access
  - Automatic file organization

- **Inference Providers**
  - OpenAI API integration
  - VLLM support
  - Strategy pattern for multiple providers

- **Monitoring & Health**
  - Comprehensive health checks
  - System metrics (CPU, memory, disk)
  - User and workspace statistics
  - Performance monitoring

## Tech Stack

- **Framework**: FastAPI
- **Database**: MySQL with SQLModel
- **Authentication**: JWT RS256
- **File Storage**: MinIO
- **2FA**: TOTP (pyotp)
- **Testing**: pytest with coverage
- **Documentation**: Auto-generated OpenAPI

## Quick Start

### Prerequisites

- Python 3.13+
- MySQL 8.0+
- MinIO (optional, for file storage)
- OpenAI API key (optional, for AI features)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd private-chat-interface/backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Set up MySQL database**
   ```sql
   CREATE DATABASE chat_db;
   CREATE USER 'chat_user'@'localhost' IDENTIFIED BY 'chat_password';
   GRANT ALL PRIVILEGES ON chat_db.* TO 'chat_user'@'localhost';
   FLUSH PRIVILEGES;
   ```

6. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

7. **Start the application**
   ```bash
   uvicorn src.main:app --reload
   ```

The API will be available at `http://localhost:8000`

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MYSQL_HOST` | MySQL host | localhost |
| `MYSQL_PORT` | MySQL port | 3306 |
| `MYSQL_USER` | MySQL username | chat_user |
| `MYSQL_PASSWORD` | MySQL password | chat_password |
| `MYSQL_DATABASE` | MySQL database name | chat_db |
| `JWT_PRIVATE_KEY_PATH` | Path to JWT private key | keys/private.pem |
| `JWT_PUBLIC_KEY_PATH` | Path to JWT public key | keys/public.pem |
| `MINIO_ENDPOINT` | MinIO endpoint | localhost:9000 |
| `MINIO_ACCESS_KEY` | MinIO access key | minioadmin |
| `MINIO_SECRET_KEY` | MinIO secret key | minioadmin |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `VLLM_ENDPOINT` | VLLM endpoint | - |

### JWT Key Generation

The application automatically generates RSA key pairs for JWT signing. Keys are stored in the `keys/` directory.

## API Endpoints

### Authentication
- `POST /auth/setup` - Setup first admin user
- `POST /auth/login` - User login
- `POST /auth/login/2fa` - Complete login with 2FA
- `POST /auth/refresh` - Refresh access token
- `POST /auth/2fa/setup` - Setup 2FA
- `POST /auth/2fa/verify` - Verify 2FA setup
- `GET /auth/me` - Get current user info

### Users
- `GET /users/` - List all users (admin)
- `POST /users/` - Create user (admin)
- `GET /users/{user_id}` - Get user details
- `PUT /users/{user_id}` - Update user
- `DELETE /users/{user_id}` - Delete user (admin)

### Workspaces
- `GET /workspaces/` - List user workspaces
- `POST /workspaces/` - Create workspace
- `GET /workspaces/{workspace_id}` - Get workspace details
- `PUT /workspaces/{workspace_id}` - Update workspace
- `DELETE /workspaces/{workspace_id}` - Delete workspace
- `POST /workspaces/{workspace_id}/invite` - Invite user to workspace

### Chats
- `GET /workspaces/{workspace_id}/chats/history` - Get workspace chats
- `POST /workspaces/{workspace_id}/chat` - Create chat
- `GET /workspaces/{workspace_id}/chat/{chat_id}` - Get chat with messages
- `GET /workspaces/{workspace_id}/chat/{chat_id}/messages` - Get paginated messages
- `POST /workspaces/{workspace_id}/chat/{chat_id}/message` - Send message

### Health & Metrics
- `GET /health/` - Basic health check
- `GET /health/detailed` - Detailed health check
- `GET /health/database` - Database health
- `GET /health/storage` - Storage health
- `GET /health/inference` - Inference providers health
- `GET /metrics/performance` - System performance metrics
- `GET /metrics/users` - User metrics
- `GET /metrics/workspaces` - Workspace metrics
- `GET /metrics/chats` - Chat metrics

## Testing

### Run Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_auth.py

# Run tests with markers
pytest -m "unit"
```

### Test Structure
```
tests/
├── conftest.py          # Test configuration and fixtures
├── test_auth.py         # Authentication tests
├── test_users.py        # User management tests
├── test_workspaces.py   # Workspace tests
└── test_chats.py        # Chat and messaging tests
```

## Development

### Code Quality
```bash
# Format code
black src/

# Sort imports
isort src/

# Lint code
flake8 src/

# Type checking
mypy src/
```

### Database Migrations

This project uses Alembic for database migrations.

```bash
# Create new migration
alembic revision --autogenerate -m "migration message"

# Apply migrations
alembic upgrade head

# Downgrade
alembic downgrade -1
```

## Docker Deployment

### Using Docker Compose

1. **Update docker-compose.yml**
   ```yaml
   version: '3.8'
   services:
     backend:
       build: ./backend
       ports:
         - "8000:8000"
       environment:
         - MYSQL_HOST=mysql
         - MYSQL_PORT=3306
         - MYSQL_USER=chat_user
         - MYSQL_PASSWORD=chat_password
         - MYSQL_DATABASE=chat_db
       depends_on:
         - mysql
         - minio

     mysql:
       image: mysql:8.0
       environment:
         MYSQL_ROOT_PASSWORD: rootpassword
         MYSQL_DATABASE: chat_db
         MYSQL_USER: chat_user
         MYSQL_PASSWORD: chat_password

     minio:
       image: minio/minio
       environment:
         MINIO_ACCESS_KEY: minioadmin
         MINIO_SECRET_KEY: minioadmin
       command: server /data
   ```

2. **Build and run**
   ```bash
   docker-compose up --build
   ```

## Security Considerations

- JWT tokens expire quickly (15 minutes for access, 30 days for refresh)
- Passwords are hashed with bcrypt
- 2FA is available for enhanced security
- CORS is configured for allowed origins only
- Rate limiting is implemented
- Input validation with Pydantic
- SQL injection prevention with SQLModel

## Monitoring

The application provides comprehensive monitoring:

- **Health Checks**: System component status
- **Metrics**: Performance and usage statistics
- **Logging**: Structured logging with configurable levels
- **Error Tracking**: Proper error handling and reporting

## Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## API Documentation

Once the application is running, visit `http://localhost:8000/docs` for interactive API documentation powered by Swagger UI.
