from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Optional

ENV_FILE = Path(__file__).parent.parent / ".env"

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./tontine.db"
    SECRET_KEY: str = "tontine_secret_key_2025"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # MTN MoMo
    MTN_API_KEY: Optional[str] = None
    MTN_USER_ID: Optional[str] = None
    MTN_USER_SECRET: Optional[str] = None
    MTN_SUBSCRIPTION_KEY: Optional[str] = None

    # Orange Money
    ORANGE_CLIENT_ID: Optional[str] = None
    ORANGE_CLIENT_SECRET: Optional[str] = None

    class Config:
        env_file = str(ENV_FILE)
        env_file_encoding = "utf-8"

settings = Settings()