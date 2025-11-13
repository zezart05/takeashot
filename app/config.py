from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    SECRET_KEY: str = os.getenv("SECRET_KEY", "akDSALASKFHL37ty934hfh34hf39fh9374fh937fh3hd4ostgh9sg")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./takeashot.db")
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    class Config:
        case_sensitive = True

settings = Settings()