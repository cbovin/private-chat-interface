"""
Application configuration settings.
"""
import secrets
from typing import List, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "Private Chat Interface"
    debug: bool = False
    secret_key: str = secrets.token_urlsafe(32)
    allowed_origins: str = "http://localhost:3000,http://localhost:8080"
    trusted_hosts: str = "localhost,127.0.0.1"

    # Database
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "chat_user"
    mysql_password: str = "chat_password"
    mysql_database: str = "chat_db"

    @property
    def database_url(self) -> str:
        """Generate MySQL database URL."""
        return f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"

    @property
    def allowed_origins_list(self) -> List[str]:
        """Parse allowed origins from comma-separated string."""
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def trusted_hosts_list(self) -> Optional[List[str]]:
        """Parse trusted hosts from comma-separated string."""
        if not self.trusted_hosts:
            return None
        return [host.strip() for host in self.trusted_hosts.split(",") if host.strip()]

    @property
    def allowed_file_types_list(self) -> List[str]:
        """Parse allowed file types from comma-separated string."""
        return [ftype.strip() for ftype in self.allowed_file_types.split(",") if ftype.strip()]

    # JWT Configuration
    jwt_private_key_path: str = "keys/private.pem"
    jwt_public_key_path: str = "keys/public.pem"
    jwt_algorithm: str = "RS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    # MinIO Configuration
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False
    minio_bucket_name: str = "chat-attachments"

    # Inference Providers
    openai_api_key: Optional[str] = None
    vllm_endpoint: Optional[str] = None
    default_inference_provider: str = "openai"

    # Email Configuration (for future use)
    smtp_server: Optional[str] = None
    smtp_port: Optional[int] = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_tls: str = "true"
    from_email: str = "noreply@yourdomain.com"

    # Redis Configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None

    # Security
    bcrypt_rounds: int = 12
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds

    # 2FA Settings
    totp_issuer: str = "Private Chat Interface"
    totp_digits: int = 6
    totp_period: int = 30

    # File Upload Configuration
    max_upload_size: int = 10485760
    allowed_file_types: str = "jpg,jpeg,png,gif,pdf,doc,docx,txt,zip,rar,7z"
    upload_path: str = "/app/uploads"

    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "json"
    log_file: str = "/app/logs/app.log"

    # Monitoring and Metrics
    enable_metrics: bool = True
    metrics_port: int = 9090
    enable_health_checks: bool = True

    # Development Settings
    reload: bool = False
    workers: int = 1
    host: str = "0.0.0.0"
    port: int = 5000

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
