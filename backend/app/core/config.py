from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    mock_gov_base_url: str = "http://mock-gov:8001"
    mock_vet_base_url: str = "http://mock-vet:8002"

    class Config:
        env_file = ".env"

settings = Settings()
