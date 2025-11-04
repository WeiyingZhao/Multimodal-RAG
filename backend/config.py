import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration"""

    # OpenAI configuration
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"

    # Server configuration
    host: str = "localhost"
    port: int = 8000
    debug: bool = True

    # CORS configuration
    allowed_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Logging configuration
    log_level: str = "INFO"
    log_file: str = "logs/app.log"

    # Model configuration
    default_model: str = "gpt-4o"
    max_tokens: int = 2048
    temperature: float = 0.7

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Create global configuration instance
settings = Settings() 