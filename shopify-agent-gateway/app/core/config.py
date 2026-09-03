from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    database_url: str = "sqlite:///./phase1.db"
    shopify_api_key: Optional[str] = None
    shopify_api_secret: Optional[str] = None
    shopify_redirect_uri: str = "http://localhost:8000/auth/shopify/callback"
    app_url: str = "http://localhost:8000"
    shopify_api_version: str = "2025-10"
    encryption_key: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
