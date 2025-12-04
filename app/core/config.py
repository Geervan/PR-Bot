import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_ID: str = ""
    PRIVATE_KEY_PATH: str = ""  # Path to key file (local dev)
    PRIVATE_KEY: str = ""  # Key content directly (Railway/production)
    WEBHOOK_SECRET: str = ""
    GEMINI_API_KEYS: str = ""  # Comma-separated list of keys
    LOG_LEVEL: str = "INFO"

    @property
    def api_keys(self):
        return [key.strip() for key in self.GEMINI_API_KEYS.split(",") if key.strip()]

    @property
    def private_key_content(self) -> str:
        """Return private key content (from env var or file)."""
        if self.PRIVATE_KEY:
            return self.PRIVATE_KEY
        if self.PRIVATE_KEY_PATH and os.path.exists(self.PRIVATE_KEY_PATH):
            with open(self.PRIVATE_KEY_PATH, 'r') as f:
                return f.read()
        return ""

    class Config:
        env_file = ".env"


settings = Settings()
