"""
Pydantic BaseSettings — tất cả config đọc từ environment variables.

Có thể override qua .env file (python-dotenv).
"""

from __future__ import annotations

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # -----------------------------------------------------------------------
    # Application
    # -----------------------------------------------------------------------
    APP_NAME: str = "Compliance Engine"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # -----------------------------------------------------------------------
    # PostgreSQL (shared instance với Backstage, database riêng: compliance)
    # -----------------------------------------------------------------------
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5433  # 5433 tránh conflict khi dev local; trên EKS dùng 5432
    POSTGRES_USER: str = "compliance"
    POSTGRES_PASSWORD: str = "compliance_password"
    POSTGRES_DB: str = "compliance"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def DATABASE_URL_SYNC(self) -> str:
        """Sync URL cho Alembic migrations."""
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # -----------------------------------------------------------------------
    # Redis
    # -----------------------------------------------------------------------
    REDIS_URL: str = "redis://localhost:6379/0"

    # Cache TTLs (seconds)
    CACHE_TTL_SCORES: int = 300  # 5 phút
    CACHE_TTL_FINDINGS: int = 300  # 5 phút
    CACHE_TTL_AI_RECOMMENDATIONS: int = 1800  # 30 phút

    # -----------------------------------------------------------------------
    # Gemini AI
    # -----------------------------------------------------------------------
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # -----------------------------------------------------------------------
    # Kubernetes
    # -----------------------------------------------------------------------
    KUBECONFIG: Optional[str] = None  # None = in-cluster config
    K8S_IN_CLUSTER: bool = False  # True khi chạy trong Pod

    # -----------------------------------------------------------------------
    # Compliance Engine behavior
    # -----------------------------------------------------------------------
    # Namespace filter mặc định (None = tất cả namespaces)
    DEFAULT_NAMESPACE_FILTER: Optional[str] = None

    # Scan interval (seconds) cho background scheduler
    SCAN_INTERVAL_SECONDS: int = 1800  # 30 phút

    # Scoring
    MAX_PENALTY_PER_CRITICAL: int = 15  # -15 điểm mỗi CRITICAL
    MAX_PENALTY_PER_HIGH: int = 5  # -5 điểm mỗi HIGH


# Singleton instance
settings = Settings()
