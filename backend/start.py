#!/usr/bin/env python3
"""
Multimodal RAG Workbench Backend Startup Script
"""

import os
import sys
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Set environment variables
from env_config import setup_environment
setup_environment()

def check_environment():
    """Check environment configuration"""
    print("🔍 Checking environment configuration...")

    # Check .env file
    env_file = current_dir / ".env"
    if not env_file.exists():
        print("⚠️  .env file not found, using default configuration")
        print("💡 Recommended: create .env file and configure OPENAI_API_KEY")

    # Check OpenAI API Key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  OPENAI_API_KEY not configured")
        print("💡 Please set in .env file: OPENAI_API_KEY=your_api_key")
    else:
        print(f"✅ OpenAI API Key configured (first 6 chars: {api_key[:6]}...)")

    # Check logs directory
    logs_dir = current_dir / "logs"
    if not logs_dir.exists():
        logs_dir.mkdir(exist_ok=True)
        print(f"📁 Created logs directory: {logs_dir}")

    print("✅ Environment check complete\n")

def install_dependencies():
    """Check and install dependencies"""
    print("📦 Checking dependency packages...")

    try:
        import fastapi
        import uvicorn
        import langchain
        print("✅ Main dependency packages installed")
    except ImportError as e:
        print(f"❌ Missing dependency package: {e}")
        print("💡 Please run: pip install -r requirements.txt")
        return False

    return True

def main():
    """Main function"""
    print("🚀 Starting Multimodal RAG Workbench Backend Service")
    print("=" * 50)

    # Check environment
    check_environment()

    # Check dependencies
    if not install_dependencies():
        sys.exit(1)

    # Start service
    print("🌟 Starting FastAPI service...")
    print("📍 API Documentation: http://localhost:8000/docs")
    print("💬 Streaming Chat: http://localhost:8000/api/chat/stream")
    print("⏹️  Stop Service: Ctrl+C")
    print("-" * 50)

    try:
        # Use uvicorn command line mode to avoid import issues
        import subprocess

        cmd = [
            sys.executable,
            "-m", "uvicorn",
            "main:app",
            "--host", "localhost",
            "--port", "8000"
        ]

        print(f"🚀 Executing command: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)

    except KeyboardInterrupt:
        print("\n👋 Service stopped")
    except Exception as e:
        print(f"❌ Startup failed: {e}")
        print(f"💡 You can also run directly: python -m uvicorn main:app --host localhost --port 8000 --reload")
        sys.exit(1)

if __name__ == "__main__":
    main() 