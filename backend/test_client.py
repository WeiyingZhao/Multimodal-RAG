#!/usr/bin/env python3
"""
Test Client - For testing streaming chat interface
"""

import asyncio
import httpx
import json
from typing import AsyncGenerator

async def test_streaming_chat():
    """Test streaming chat interface"""
    print("🧪 Testing streaming chat interface...")

    url = "http://localhost:8000/api/chat/stream"

    # Test request data
    test_data = {
        "content": "Hello! Please introduce your features.",
        "history": [],
        "model": "gpt-4o",
        "knowledge_base": "default"
    }
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                url,
                json=test_data,
                headers={"Accept": "text/event-stream"}
            ) as response:

                print(f"Status code: {response.status_code}")
                print("=" * 50)
                print("📨 Streaming response:")

                full_content = ""
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])  # Remove "data: " prefix

                            if data["type"] == "content_delta":
                                content = data["content"]
                                print(content, end="", flush=True)
                                full_content += content
                            elif data["type"] == "message_complete":
                                print("\n" + "=" * 50)
                                print(f"✅ Response complete")
                                print(f"📄 Full content length: {len(data['full_content'])} characters")
                                break
                            elif data["type"] == "error":
                                print(f"\n❌ Error: {data['error']}")
                                break

                        except json.JSONDecodeError:
                            continue

                print(f"\n✅ Test complete")

    except Exception as e:
        print(f"❌ Test failed: {e}")

async def test_sync_chat():
    """Test synchronous chat interface"""
    print("\n🧪 Testing synchronous chat interface...")

    url = "http://localhost:8000/api/chat"

    test_data = {
        "content": "Briefly introduce LangChain",
        "history": [],
        "model": "gpt-4o",
        "knowledge_base": "default"
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=test_data)

            print(f"Status code: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print("📨 Synchronous response:")
                print(f"Role: {result['role']}")
                print(f"Timestamp: {result['timestamp']}")
                print(f"Content: {result['content']}")
                print("✅ Test complete")
            else:
                print(f"❌ Response error: {response.text}")

    except Exception as e:
        print(f"❌ Test failed: {e}")

async def test_health():
    """Test health check endpoint"""
    print("🧪 Testing health check endpoint...")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/")

            print(f"Status code: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print("📊 Service status:")
                for key, value in result.items():
                    print(f"  {key}: {value}")
                print("✅ Service running normally")
            else:
                print(f"❌ Service abnormal: {response.text}")

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("💡 Please ensure backend service is running: python start.py")

async def main():
    """Main test function"""
    print("🚀 Starting API interface testing")
    print("=" * 60)

    # Test health check
    await test_health()

    # Test synchronous interface
    await test_sync_chat()

    # Test streaming interface
    await test_streaming_chat()

    print("\n🎉 All tests complete!")

if __name__ == "__main__":
    asyncio.run(main()) 