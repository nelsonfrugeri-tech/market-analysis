"""Application configuration loaded from environment / .env file.

Single source of truth for all configurable values.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from market_analysis.domain.schemas import RetryPolicy


class AppSettings(BaseSettings):
    """Top-level application configuration."""

    model_config = SettingsConfigDict(
        env_prefix="MA_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # --- Database ---
    db_path: Path = Field(
        default=Path("data/market_analysis.db"),
        description="Path to the SQLite database file",
    )

    # --- Target fund ---
    fund_cnpj: str = Field(
        default="43.121.002/0001-41",
        description="CNPJ of the fund to analyze",
    )

    # --- Collection schedule ---
    collection_hour: int = Field(default=9, ge=0, le=23)
    collection_minute: int = Field(default=0, ge=0, le=59)

    # --- Retry ---
    retry_max_attempts: int = Field(default=3, ge=1)
    retry_base_delay: float = Field(default=2.0, ge=0.1)
    retry_max_delay: float = Field(default=60.0, ge=1.0)

    # --- SMTP ---
    smtp_host: str = Field(default="")
    smtp_port: int = Field(default=587)
    smtp_username: str = Field(default="")
    smtp_password: str = Field(default="")
    smtp_use_tls: bool = Field(default=True)
    smtp_sender_email: str = Field(default="")

    # --- Logging ---
    log_level: str = Field(default="INFO")

    def get_retry_policy(self) -> RetryPolicy:
        """Build a RetryPolicy from settings."""
        return RetryPolicy(
            max_attempts=self.retry_max_attempts,
            base_delay_seconds=self.retry_base_delay,
            max_delay_seconds=self.retry_max_delay,
        )
