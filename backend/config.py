"""
Backend Configuration
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Application
    APP_NAME: str = "Dating Wizard API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # API
    API_V1_PREFIX: str = "/api"

    # CORS
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost",
    ]

    # Database
    DATABASE_URL: str = "sqlite:///./data/dating_wizard.db"

    # File Upload
    UPLOAD_DIR: Path = Path("uploads")
    REFERENCE_IMAGES_DIR: Path = UPLOAD_DIR / "reference_images"
    SCREENSHOTS_DIR: Path = UPLOAD_DIR / "screenshots"
    THUMBNAILS_DIR: Path = UPLOAD_DIR / "thumbnails"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB

    # Classifier
    PREFERENCES_PATH: str = "config/preferences.json"

    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()

# Ensure directories exist
settings.REFERENCE_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
settings.SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
settings.THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)
Path("data").mkdir(exist_ok=True)
