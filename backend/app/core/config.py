from pydantic_settings import BaseSettings
from typing import List
import json


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/ashkeeper"
    SECRET_KEY: str = "change-this-secret"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days

    # Stored as JSON string in env, parsed here
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3005",
        "http://127.0.0.1:3005",
    ]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def model_post_init(self, __context):
        # Handle CORS_ORIGINS as JSON string if passed as string
        if isinstance(self.CORS_ORIGINS, str):
            try:
                object.__setattr__(self, 'CORS_ORIGINS', json.loads(self.CORS_ORIGINS))
            except Exception:
                pass


settings = Settings()
