#!/usr/bin/env python3
"""
Environment Configuration Settings
Please set your OpenAI API Key before use
"""

import os
from dotenv import load_dotenv

load_dotenv(override=True)

def setup_environment():
    """Set environment variables"""

    # OpenAI configuration
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Please set your OPENAI_API_KEY")
        print("💡 Set in .env file: OPENAI_API_KEY=your_actual_api_key")
        print("💡 Or set in system environment variables")
        # API key should be set in .env file or environment variables
        os.environ["OPENAI_API_KEY"] = ""

    os.environ["OPENAI_BASE_URL"] = "https://api.openai.com/v1"

    # Server configuration
    os.environ["HOST"] = "localhost"
    os.environ["PORT"] = "8000"
    os.environ["DEBUG"] = "True"

    # Logging configuration
    os.environ["LOG_LEVEL"] = "INFO"

    # Model configuration
    os.environ["DEFAULT_MODEL"] = "gpt-4o"
    os.environ["MAX_TOKENS"] = "2048"
    os.environ["TEMPERATURE"] = "0.7"

    # OCR configuration - Tesseract
    tessdata_path = r"C:\ProgramData\anaconda3\envs\rag\share\tessdata"
    os.environ["TESSDATA_PREFIX"] = tessdata_path
    print(f"✅ TESSDATA_PREFIX set: {tessdata_path}")

if __name__ == "__main__":
    setup_environment()
    print("✅ Environment variables setup complete")
    print("💡 Please modify OPENAI_API_KEY in env_config.py") 