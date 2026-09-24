"""
FLIP Core API — Settings via Pydantic BaseSettings
All values are loaded from environment variables (or .env.local).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AnyUrl, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": (".env", ".env.local"), "case_sensitive": False, "extra": "ignore"}

    # ------- Runtime -------
    FLIP_ENV: Literal["local", "staging", "production"] = "local"
    API_VERSION: str = "3.0.0"

    # ------- Database -------
    DATABASE_URL: str = Field(default="postgresql+asyncpg://postgres:postgres@localhost:5432/flip_db", description="Async SQLAlchemy URL (postgresql+asyncpg://...)")
    DATABASE_URL_SYNC: str | None = None
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30

    # ------- NATS -------
    NATS_URL: str = "nats://localhost:4222"
    NATS_JETSTREAM_DOMAIN: str = "flip"

    # ------- Keycloak / Auth -------
    KEYCLOAK_URL: str = "http://localhost:8080"
    KEYCLOAK_REALM: str = "flip"
    KEYCLOAK_CLIENT_ID: str = "flip-api"
    KEYCLOAK_CLIENT_SECRET: SecretStr = Field(default="dev-secret")
    KEYCLOAK_ADMIN_CLIENT_ID: str = "flip-api"
    KEYCLOAK_ADMIN_CLIENT_SECRET: SecretStr = Field(default="dev-secret")
    KEYCLOAK_ADMIN_USER: str = "admin"
    KEYCLOAK_ADMIN_PASSWORD: SecretStr = Field(default="admin")
    KEYCLOAK_JWKS_URL: str | None = None

    @property
    def jwks_url(self) -> str:
        if self.KEYCLOAK_JWKS_URL:
            return self.KEYCLOAK_JWKS_URL
        return f"{self.KEYCLOAK_URL}/realms/{self.KEYCLOAK_REALM}/protocol/openid-connect/certs"

    # ------- Cache / Redis -------
    REDIS_URL: str = "redis://localhost:6379/0"

    # ------- Rate Limits -------
    RATE_LIMIT_LOGIN_PER_MIN: int = 5
    RATE_LIMIT_OTP_PER_HOUR: int = 3
    RATE_LIMIT_SYNC_PER_MIN: int = 10

    # ------- MinIO / S3 -------
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: SecretStr = Field(default="minioadmin")
    MINIO_BUCKET_MODELS: str = "flip-models"
    MINIO_BUCKET_IMAGES: str = "flip-images"
    MINIO_BUCKET_TILES: str = "flip-tiles"
    MINIO_BUCKET_FIRMWARE: str = "flip-firmware"

    # ------- Temporal -------
    TEMPORAL_ADDRESS: str = "localhost:7233"
    TEMPORAL_NAMESPACE: str = "flip"
    TEMPORAL_TASK_QUEUE: str = "flip-default"

    # ------- MLflow -------
    MLFLOW_TRACKING_URI: str = "http://localhost:5000"

    # ------- Copilot / Voice -------
    RASA_URL: str = "http://localhost:5005"
    WHISPER_URL: str = "http://localhost:9999"   # whisper.cpp server

    # ------- Notification Providers -------
    IMD_API_KEY: SecretStr | None = None
    TWILIO_ACCOUNT_SID: SecretStr | None = None
    TWILIO_AUTH_TOKEN: SecretStr | None = None
    TWILIO_VERIFY_SERVICE_SID: SecretStr | None = None
    TWILIO_PHONE_NUMBER: str | None = None
    FLIP_OTP_MOCK_ENABLED: bool = True
    WHATSAPP_TOKEN: SecretStr | None = None
    WHATSAPP_PHONE_NUMBER_ID: str | None = None
    FCM_SERVER_KEY: SecretStr | None = None

    # ------- CORS -------
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "https://staging.flip.farm",
        "https://flip.farm",
    ]

    # ------- Observability -------
    SENTRY_DSN: str | None = None
    LOG_LEVEL: str = "info"

    # ------- Security -------
    JWT_SECRET: SecretStr = Field(default="dev-jwt-secret")
    ENCRYPTION_KEY: SecretStr = Field(default="dev-encryption-key")
    ALLOWED_HOSTS: list[str] = ["*"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings: Settings = get_settings()
