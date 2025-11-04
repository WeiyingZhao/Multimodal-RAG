import os
import json
import asyncio
from typing import List, Dict, Any, AsyncGenerator
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from loguru import logger

# LangChain 1.0 imports
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.callbacks import AsyncCallbackHandler

# Local configuration
from config import settings

# Load environment variables
load_dotenv(override=True)

# Configure logging
logger.add(settings.log_file, rotation="500 MB", level=settings.log_level)

app = FastAPI(
    title="Multimodal RAG Workbench API",
    description="Intelligent conversation API based on LangChain 1.0",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request models
class MessageRequest(BaseModel):
    content: str = Field(..., description="User message content")
    history: List[Dict[str, Any]] = Field(default=[], description="Conversation history")
    model: str = Field(default="gpt-4o", description="Model to use")
    knowledge_base: str = Field(default="default", description="Knowledge base name")

class MessageResponse(BaseModel):
    content: str
    role: str
    timestamp: str
    references: List[Dict[str, Any]] = Field(default=[])

# Streaming callback handler
class StreamingCallbackHandler(AsyncCallbackHandler):
    def __init__(self):
        self.tokens = []
        self.current_chunk = ""

    async def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """Handle new token"""
        self.tokens.append(token)
        self.current_chunk += token

# Initialize chat model
def get_chat_model(model_name: str = None):
    """Initialize chat model"""
    if model_name is None:
        model_name = settings.default_model
        
    try:
        # Use LangChain 1.0's new way to initialize model
        model = init_chat_model(
            f"openai:{model_name}",
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
            streaming=True
        )
        return model
    except Exception as e:
        logger.error(f"Model initialization failed: {e}")
        raise HTTPException(status_code=500, detail=f"Model initialization failed: {str(e)}")

def convert_history_to_messages(history: List[Dict[str, Any]]) -> List[BaseMessage]:
    """Convert history to LangChain message format"""
    messages = []

    # Add system message
    system_prompt = """You are a professional multimodal RAG assistant with the following capabilities:
1. Document understanding and analysis
2. Image content recognition
3. Audio transcription and analysis
4. Knowledge retrieval and Q&A

Please answer user questions in a professional and friendly manner, providing detailed explanations when needed."""

    messages.append(SystemMessage(content=system_prompt))

    # Convert history messages
    for msg in history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))
    
    return messages

async def generate_streaming_response(
    messages: List[BaseMessage],
    model_name: str
) -> AsyncGenerator[str, None]:
    """Generate streaming response"""
    try:
        model = get_chat_model(model_name)

        # Create streaming response
        full_response = ""
        chunk_buffer = ""

        async for chunk in model.astream(messages):
            if hasattr(chunk, 'content') and chunk.content:
                content = chunk.content
                full_response += content
                chunk_buffer += content

                # Send chunks by sentence or phrase
                if any(delimiter in chunk_buffer for delimiter in ['.', '。', '!', '！', '?', '？', '\n']):
                    # Construct SSE format data
                    data = {
                        "type": "content_delta",
                        "content": chunk_buffer,
                        "timestamp": datetime.now().isoformat()
                    }
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                    chunk_buffer = ""
                else:
                    # Send individual character
                    data = {
                        "type": "content_delta",
                        "content": content,
                        "timestamp": datetime.now().isoformat()
                    }
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

        # Send remaining content
        if chunk_buffer:
            data = {
                "type": "content_delta",
                "content": chunk_buffer,
                "timestamp": datetime.now().isoformat()
            }
            yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

        # Send completion signal
        final_data = {
            "type": "message_complete",
            "full_content": full_response,
            "timestamp": datetime.now().isoformat(),
            "references": []  # Empty for now, can add RAG references later
        }
        yield f"data: {json.dumps(final_data, ensure_ascii=False)}\n\n"

    except Exception as e:
        logger.error(f"Streaming response generation failed: {e}")
        error_data = {
            "type": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Multimodal RAG Workbench API",
        "version": "1.0.0",
        "status": "running",
        "langchain_version": "1.0.0"
    }

@app.post("/api/chat/stream")
async def chat_stream(request: MessageRequest):
    """Streaming chat endpoint"""
    try:
        logger.info(f"Received chat request: {request.content[:100]}...")

        # Convert message history
        messages = convert_history_to_messages(request.history)

        # Add current user message
        messages.append(HumanMessage(content=request.content))

        # Return streaming response
        return StreamingResponse(
            generate_streaming_response(messages, request.model),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
            }
        )

    except Exception as e:
        logger.error(f"Chat request processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat_sync(request: MessageRequest):
    """Synchronous chat endpoint (non-streaming)"""
    try:
        logger.info(f"Received synchronous chat request: {request.content[:100]}...")

        # Convert message history
        messages = convert_history_to_messages(request.history)
        messages.append(HumanMessage(content=request.content))

        # Get model response
        model = get_chat_model(request.model)
        response = await model.ainvoke(messages)

        return MessageResponse(
            content=response.content,
            role="assistant",
            timestamp=datetime.now().isoformat(),
            references=[]
        )

    except Exception as e:
        logger.error(f"Synchronous chat request processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/models")
async def get_models():
    """Get available model list"""
    return {
        "models": [
            {
                "id": "gpt-4o",
                "name": "GPT-4O",
                "description": "Latest GPT-4 optimized version"
            },
            {
                "id": "gpt-4o-mini",
                "name": "GPT-4O Mini",
                "description": "Lightweight GPT-4 version"
            },
            {
                "id": "gpt-5",
                "name": "GPT-5",
                "description": "Next generation GPT model (if available)"
            }
        ]
    }

@app.get("/api/knowledge-bases")
async def get_knowledge_bases():
    """Get knowledge base list"""
    return {
        "knowledge_bases": [
            {
                "id": "default",
                "name": "Default Knowledge Base",
                "description": "General knowledge base"
            },
            {
                "id": "technical",
                "name": "Technical Documentation",
                "description": "Technical documentation repository"
            }
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host=settings.host, 
        port=settings.port,
        log_level=settings.log_level.lower()
    ) 
