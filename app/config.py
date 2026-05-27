from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Optional

ENV_FILE = Path(__file__).parent.parent / ".env"

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres.ehurmyiltyvaewowcrwl:Joelomega%40237@aws-0-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require"
    SECRET_KEY: str = "tontine_secret_key_2025"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # ───────── PawaPay ─────────
    PAWAPAY_API_KEY: Optional[str] = None

    PAWAPAY_MODE: str = "sandbox"

    PAWAPAY_API_SANDBOX_URL: str = "https://api.sandbox.pawapay.io/v2"

    PAWAPAY_API_PRODUCTION_URL: str = "https://api.pawapay.io/v2"

    PAWAPAY_CALLBACK_URL: str = "https://ton-backend.onrender.com/payments/callback"

    class Config:
        env_file = str(ENV_FILE)
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()