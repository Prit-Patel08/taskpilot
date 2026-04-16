from functools import lru_cache

from pydantic import Field
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(
        default="postgresql+asyncpg://taskpilot:taskpilot@postgres:5432/taskpilot",
        validation_alias="DATABASE_URL",
    )
    aws_region: str = Field(
        default="us-east-1",
        validation_alias="AWS_REGION",
    )
    resume_queue_url: str = Field(default="", validation_alias="RESUME_QUEUE_URL")
    ats_queue_url: str = Field(default="", validation_alias="ATS_QUEUE_URL")
    scoring_queue_url: str = Field(default="", validation_alias="SCORING_QUEUE_URL")
    apply_queue_url: str = Field(default="", validation_alias="APPLY_QUEUE_URL")
    tracking_queue_url: str = Field(default="", validation_alias="TRACKING_QUEUE_URL")
    sqs_wait_time_seconds: int = Field(
        default=10,
        validation_alias="SQS_WAIT_TIME_SECONDS",
    )
    sqs_visibility_timeout_seconds: int = Field(
        default=60,
        validation_alias="SQS_VISIBILITY_TIMEOUT_SECONDS",
    )
    sqs_max_number_of_messages: int = Field(
        default=5,
        validation_alias="SQS_MAX_NUMBER_OF_MESSAGES",
    )
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
    application_processing_timeout_seconds: int = Field(
        default=30,
        validation_alias="APPLICATION_PROCESSING_TIMEOUT_SECONDS",
    )
    application_heartbeat_interval_seconds: float = Field(
        default=5.0,
        validation_alias="APPLICATION_HEARTBEAT_INTERVAL_SECONDS",
    )
    heartbeat_interval_seconds: float = Field(
        default=5.0,
        validation_alias="HEARTBEAT_INTERVAL_SECONDS",
    )
    stuck_job_scan_interval_seconds: float = Field(
        default=10,
        validation_alias="STUCK_JOB_SCAN_INTERVAL_SECONDS",
    )
    stuck_job_scan_jitter_seconds: float = Field(
        default=2.0,
        validation_alias="STUCK_JOB_SCAN_JITTER_SECONDS",
    )
    stuck_job_scan_batch_size: int = Field(
        default=50,
        validation_alias="STUCK_JOB_SCAN_BATCH_SIZE",
    )
    s3_region: str = Field(
        default="us-east-1",
        validation_alias="S3_REGION",
    )
    s3_bucket_name: str = Field(
        default="taskpilot-private",
        validation_alias="S3_BUCKET_NAME",
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
    max_upload_size_bytes: int = Field(
        default=10 * 1024 * 1024,
        validation_alias="MAX_UPLOAD_SIZE_BYTES",
    )

    @model_validator(mode="after")
    def validate_timing_configuration(self) -> "Settings":
        effective_heartbeat_interval = min(
            self.application_heartbeat_interval_seconds,
            self.heartbeat_interval_seconds,
        )
        self.application_heartbeat_interval_seconds = effective_heartbeat_interval
        self.heartbeat_interval_seconds = effective_heartbeat_interval

        minimum_timeout = effective_heartbeat_interval * 3
        if self.application_processing_timeout_seconds < minimum_timeout:
            raise ValueError(
                "APPLICATION_PROCESSING_TIMEOUT_SECONDS must be at least 3 * HEARTBEAT_INTERVAL_SECONDS"
            )

        if self.stuck_job_scan_interval_seconds <= 0:
            raise ValueError("STUCK_JOB_SCAN_INTERVAL_SECONDS must be greater than 0")
        if self.stuck_job_scan_jitter_seconds < 0:
            raise ValueError("STUCK_JOB_SCAN_JITTER_SECONDS must be >= 0")

        return self

    @model_validator(mode="after")
    def normalize_optional_storage_values(self) -> "Settings":
        self.resume_queue_url = self.resume_queue_url.strip()
        self.ats_queue_url = self.ats_queue_url.strip()
        self.scoring_queue_url = self.scoring_queue_url.strip()
        self.apply_queue_url = self.apply_queue_url.strip()
        self.tracking_queue_url = self.tracking_queue_url.strip()
        if not self.resume_queue_url:
            raise ValueError("RESUME_QUEUE_URL must be configured")
        if not self.ats_queue_url:
            raise ValueError("ATS_QUEUE_URL must be configured")
        if not self.scoring_queue_url:
            raise ValueError("SCORING_QUEUE_URL must be configured")
        if not self.apply_queue_url:
            raise ValueError("APPLY_QUEUE_URL must be configured")
        if not self.tracking_queue_url:
            raise ValueError("TRACKING_QUEUE_URL must be configured")
        self.aws_access_key_id = (
            self.aws_access_key_id.strip() if self.aws_access_key_id else None
        )
        self.aws_secret_access_key = (
            self.aws_secret_access_key.strip() if self.aws_secret_access_key else None
        )
        self.aws_session_token = (
            self.aws_session_token.strip() if self.aws_session_token else None
        )
        self.s3_endpoint_url = (
            self.s3_endpoint_url.strip() if self.s3_endpoint_url else None
        )
        if self.max_upload_size_bytes <= 0:
            raise ValueError("MAX_UPLOAD_SIZE_BYTES must be greater than 0")
        if self.sqs_wait_time_seconds <= 0 or self.sqs_wait_time_seconds > 20:
            raise ValueError("SQS_WAIT_TIME_SECONDS must be between 1 and 20")
        if self.sqs_visibility_timeout_seconds <= 0:
            raise ValueError("SQS_VISIBILITY_TIMEOUT_SECONDS must be greater than 0")
        if self.sqs_max_number_of_messages <= 0 or self.sqs_max_number_of_messages > 10:
            raise ValueError("SQS_MAX_NUMBER_OF_MESSAGES must be between 1 and 10")
        if self.outbox_batch_size <= 0:
            raise ValueError("OUTBOX_BATCH_SIZE must be greater than 0")
        if self.outbox_max_attempts <= 0:
            raise ValueError("OUTBOX_MAX_ATTEMPTS must be greater than 0")
        if self.outbox_retry_base_delay_seconds <= 0:
            raise ValueError("OUTBOX_RETRY_BASE_DELAY_SECONDS must be greater than 0")
        if self.outbox_processing_timeout_seconds <= 0:
            raise ValueError("OUTBOX_PROCESSING_TIMEOUT_SECONDS must be greater than 0")
        if self.outbox_poll_interval_seconds <= 0:
            raise ValueError("OUTBOX_POLL_INTERVAL_SECONDS must be greater than 0")
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
