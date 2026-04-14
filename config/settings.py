"""Configuration management for Teamie scraper."""

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Teamie Configuration
    TEAMIE_URL: str = "https://lms.asl.org/dash/#/"
    GOOGLE_EMAIL: Optional[str] = None  # Optional, for user reference only
    TEAMIE_USER_ID: str = "207"  # Teamie user ID for calendar URL

    # Scraper Settings
    HEADLESS: bool = False  # False for first run with Google OAuth
    BROWSER_TYPE: str = "chromium"  # chromium, firefox, webkit
    TIMEOUT: int = 30000  # milliseconds
    SLOW_MO: int = 0  # slow down operations (ms)

    # Output Settings
    OUTPUT_DIR: Path = Path("data/output")
    LOG_DIR: Path = Path("logs")
    LOG_LEVEL: str = "INFO"

    # Retry Settings
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 2  # seconds

    # Session Settings (for Google OAuth)
    USE_PERSISTENT_SESSION: bool = True
    SESSION_DIR: Path = Path("data/browser_session")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    def __init__(self, **kwargs):
        """Initialize settings and create necessary directories."""
        super().__init__(**kwargs)
        # Ensure directories exist
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.SESSION_DIR.mkdir(parents=True, exist_ok=True)
