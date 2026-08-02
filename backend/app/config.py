"""Application configuration.

Defines the :class:`Settings` model, which loads and validates configuration
values from environment variables (and an optional ``.env`` file), and
exposes a single shared ``settings`` instance for the rest of the
application to import.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Path to the ``.env`` file located at the backend project root
# (``backend/.env``), independent of the current working directory.
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    """Strongly-typed application settings.

    Values are read from environment variables first, falling back to the
    ``.env`` file at the backend project root. See ``.env.example`` for the
    full list of supported variables and their expected format.

    Attributes:
        app_name: Human-readable name of the application.
        app_version: Semantic version of the running application.
        database_url: Connection string for the primary database.
        model_path: Filesystem path where AI model artifacts are stored.
        log_level: Minimum severity level for emitted log records.
    """

    app_name: str = "AI Warehouse Safety Inspector"
    app_version: str = "1.0.0"
    database_url: str = "postgresql://postgres:password@localhost:5432/warehouse_ai"
    model_path: str = "models/"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings: Settings = Settings()
"""Singleton settings instance shared across the application."""
