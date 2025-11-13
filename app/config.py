from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    APP_NAME: str = "Take a Shot - Task Management"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev_secret_key_12345_change_in_production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./takeashot.db")
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    class Config:
        case_sensitive = True

settings = Settings()