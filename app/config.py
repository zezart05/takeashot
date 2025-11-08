from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    # Secret key - will use environment variable in production
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev_secret_key_12345_change_in_production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./takeashot.db")
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    class Config:
        case_sensitive = True

settings = Settings()