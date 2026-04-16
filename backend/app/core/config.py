from functools import lru_cache

from pydantic import Field
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://taskpilot:taskpilot@postgres:5432/taskpilot"
    redis_url: str = "redis://redis:6379/0"
    rabbitmq_url: str = Field(
        default="amqp://guest:guest@rabbitmq:5672/",
        validation_alias="RABBITMQ_URL",
    )
    application_retry_max_retries: int = Field(
        default=3,
        validation_alias="APPLICATION_RETRY_MAX_RETRIES",
    )
    application_retry_base_delay_seconds: int = Field(
        default=5,
        validation_alias="APPLICATION_RETRY_BASE_DELAY_SECONDS",
    )
    outbox_batch_size: int = Field(
        default=50,
        validation_alias="OUTBOX_BATCH_SIZE",
    )
    outbox_max_attempts: int = Field(
        default=10,
        validation_alias="OUTBOX_MAX_ATTEMPTS",
    )
    outbox_retry_base_delay_seconds: int = Field(
        default=5,
        validation_alias="OUTBOX_RETRY_BASE_DELAY_SECONDS",
    )
    outbox_processing_timeout_seconds: int = Field(
        default=30,
        validation_alias="OUTBOX_PROCESSING_TIMEOUT_SECONDS",
    )
    outbox_poll_interval_seconds: int = Field(
        default=1,
        validation_alias="OUTBOX_POLL_INTERVAL_SECONDS",
    )
    auth0_domain: str = Field(
        default="your-tenant.us.auth0.com",
        validation_alias="AUTH0_DOMAIN",
    )
    auth0_audience: str = Field(
        default="https://api.taskpilot.local",
        validation_alias="AUTH0_AUDIENCE",
    )
    auth0_algorithms: tuple[str, ...] = Field(
        default=("RS256",),
        validation_alias="AUTH0_ALGORITHMS",
    )
    auth0_jwks_cache_ttl_seconds: int = Field(
        default=300,
        validation_alias="AUTH0_JWKS_CACHE_TTL_SECONDS",
    )
    auth0_jwks_timeout_seconds: float = Field(
        default=3.0,
        validation_alias="AUTH0_JWKS_TIMEOUT_SECONDS",
    )
    dev_auth_bypass: bool = Field(
        default=False,
        validation_alias="DEV_AUTH_BYPASS",
    )
    dev_auth_subject: str = Field(
        default="dev|local-user",
        validation_alias="DEV_AUTH_SUBJECT",
    )
    dev_auth_email: str = Field(
        default="dev@taskpilot.local",
        validation_alias="DEV_AUTH_EMAIL",
    )
    cors_allowed_origins: tuple[str, ...] = Field(
        default=(
            "http://127.0.0.1:5173",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://localhost:3000",
        ),
        validation_alias="CORS_ALLOWED_ORIGINS",
    )
    s3_bucket_name: str = Field(
        default="taskpilot-private",
        validation_alias="S3_BUCKET_NAME",
    )
    s3_region: str = Field(
        default="us-east-1",
        validation_alias="S3_REGION",
    )
    aws_access_key_id: str | None = Field(
        default=None,
        validation_alias="AWS_ACCESS_KEY_ID",
    )
    aws_secret_access_key: str | None = Field(
        default=None,
        validation_alias="AWS_SECRET_ACCESS_KEY",
    )
    aws_session_token: str | None = Field(
        default=None,
        validation_alias="AWS_SESSION_TOKEN",
    )
    s3_endpoint_url: str | None = Field(
        default=None,
        validation_alias="S3_ENDPOINT_URL",
    )
    s3_public_base_url: str | None = Field(
        default=None,
        validation_alias="S3_PUBLIC_BASE_URL",
    )
    s3_presign_expiration_seconds: int = Field(
        default=600,
        validation_alias="S3_PRESIGN_EXPIRATION_SECONDS",
    )
    max_upload_size_bytes: int = Field(
        default=10 * 1024 * 1024,
        validation_alias="MAX_UPLOAD_SIZE_BYTES",
    )

    @field_validator("auth0_domain", mode="before")
    @classmethod
    def normalize_auth0_domain(cls, value: str) -> str:
        normalized = str(value).strip()
        normalized = normalized.removeprefix("https://").removeprefix("http://")
        return normalized.rstrip("/")

    @field_validator("auth0_algorithms", mode="before")
    @classmethod
    def normalize_auth0_algorithms(cls, value: object) -> tuple[str, ...]:
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                stripped = stripped.strip("[]").replace('"', "").replace("'", "")
                parts = [part.strip() for part in stripped.split(",") if part.strip()]
            else:
                parts = [part.strip() for part in stripped.split(",") if part.strip()]
            return tuple(parts) or ("RS256",)
        if isinstance(value, (list, tuple, set)):
            parts = [str(part).strip() for part in value if str(part).strip()]
            return tuple(parts) or ("RS256",)
        return ("RS256",)

    @field_validator("auth0_jwks_cache_ttl_seconds", mode="before")
    @classmethod
    def normalize_jwks_cache_ttl(cls, value: object) -> int:
        ttl = int(value)
        return ttl if ttl > 0 else 300

    @field_validator("auth0_jwks_timeout_seconds", mode="before")
    @classmethod
    def normalize_jwks_timeout(cls, value: object) -> float:
        timeout = float(value)
        return timeout if timeout > 0 else 3.0

    @field_validator("dev_auth_subject", "dev_auth_email", mode="before")
    @classmethod
    def normalize_dev_auth_strings(cls, value: object) -> str:
        return str(value).strip()

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def normalize_cors_allowed_origins(cls, value: object) -> tuple[str, ...]:
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                stripped = stripped.strip("[]").replace('"', "").replace("'", "")
            parts = [part.strip() for part in stripped.split(",") if part.strip()]
            return tuple(parts)
        if isinstance(value, (list, tuple, set)):
            return tuple(str(part).strip() for part in value if str(part).strip())
        return (
            "http://127.0.0.1:5173",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://localhost:3000",
        )

    @field_validator(
        "aws_access_key_id",
        "aws_secret_access_key",
        "aws_session_token",
        "s3_endpoint_url",
        "s3_public_base_url",
        mode="before",
    )
    @classmethod
    def normalize_optional_strings(cls, value: object) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @field_validator("s3_presign_expiration_seconds", mode="before")
    @classmethod
    def normalize_s3_presign_expiration_seconds(cls, value: object) -> int:
        expiration = int(value)
        return expiration if expiration > 0 else 600

    @field_validator("max_upload_size_bytes", mode="before")
    @classmethod
    def normalize_max_upload_size_bytes(cls, value: object) -> int:
        max_bytes = int(value)
        return max_bytes if max_bytes > 0 else 10 * 1024 * 1024

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
