"""Module: config."""

from pydantic_settings import BaseSettings

# Centralized runtime configuration loaded from environment variables.
class Settings(BaseSettings):
    # Primary SQLAlchemy connection string for the backend database.
    database_url: str
    # Base URL for mocked government integration service used in dev/test.
    mock_gov_base_url: str = "http://mock-gov:8001"
    # Base URL for mocked veterinarian integration service used in dev/test.
    mock_vet_base_url: str = "http://mock-vet:8002"

    # Configure pydantic-settings to also load values from local .env file.
    class Config:
        env_file = ".env"

# Global settings instance imported by app modules at runtime.
settings = Settings()

