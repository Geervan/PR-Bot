import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_ID: str
    PRIVATE_KEY_PATH: str
    WEBHOOK_SECRET: str
    GEMINI_API_KEYS: str  # Comma-separated list of keys
    LOG_LEVEL: str = "INFO"

    @property
    def api_keys(self):
        return [key.strip() for key in self.GEMINI_API_KEYS.split(",") if key.strip()]

    class Config:
        env_file = ".env"

settings = Settings()
