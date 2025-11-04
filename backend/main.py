import os
import json
import asyncio
import tempfile
import re
from typing import List, Dict, Any, AsyncGenerator
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from loguru import logger

# LangChain imports (using latest version standard approach)
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.callbacks import AsyncCallbackHandler

# Local configuration
from config import settings
from pdf_processor import PDFProcessor
import re

# Load environment variables
load_dotenv(override=True)

# Configure logging
logger.add(settings.log_file, rotation="500 MB", level=settings.log_level)

app = FastAPI(
    title="Multimodal RAG Workbench API",
    description="Intelligent Conversation API based on LangChain 1.0",
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

# Content block model (multimodal support)
class ContentBlock(BaseModel):
    type: str = Field(..., description="Content type: text, image, audio")
    content: str = Field(..., description="Content data")
    thumbnail: str = Field(default="", description="Thumbnail (optional)")
    transcription: str = Field(default="", description="Audio transcription text (audio type only)")

# Request model (multimodal support)
class MessageRequest(BaseModel):
    content: str = Field(default="", description="Plain text content (backward compatibility)")
    content_blocks: List[ContentBlock] = Field(default=[], description="Multimodal content blocks")
    pdf_chunks: List[Dict[str, Any]] = Field(default=[], description="PDF document chunks for reference tracing")
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

# Initialize processors
pdf_processor = PDFProcessor()

# Import audio processor
try:
    from audio_processor import AudioProcessor
    audio_processor = AudioProcessor()
    logger.info("✅ Audio processor initialized successfully")
except ImportError as e:
    logger.warning(f"⚠️ Audio processor import failed: {e}")
    audio_processor = None

# Startup dependency check
@app.on_event("startup")
async def startup_event():
    """Check required dependencies and configuration on startup"""
    logger.info("🚀 Starting service...")

    # 1. Check OpenAI API Key
    if not settings.openai_api_key or settings.openai_api_key == "":
        logger.error("❌ OPENAI_API_KEY not set!")
        logger.error("Please set OPENAI_API_KEY in environment variables or .env file")
        raise RuntimeError("OpenAI API key is required. Please set OPENAI_API_KEY environment variable.")
    logger.info("✅ OpenAI API key configured")

    # 2. Check Unstructured dependency
    try:
        from langchain_unstructured import UnstructuredLoader
        logger.info("✅ Unstructured library installed")
    except ImportError:
        logger.warning("⚠️ Unstructured library not installed, PDF OCR functionality may be limited")
        logger.warning("Recommended installation: pip install unstructured[local-inference]")

    # 3. Check Tesseract OCR
    import subprocess
    try:
        result = subprocess.run(['tesseract', '--version'],
                              capture_output=True,
                              text=True,
                              timeout=5)
        if result.returncode == 0:
            version = result.stdout.split('\n')[0]
            logger.info(f"✅ Tesseract OCR installed: {version}")
        else:
            logger.warning("⚠️ Tesseract OCR may not be properly installed")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        logger.warning("⚠️ Tesseract OCR not installed, scanned PDF processing will fail")
        logger.warning("Installation guide: https://tesseract-ocr.github.io/tessdoc/Installation.html")

    logger.info("✅ Service startup complete!")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    logger.info("👋 Service shutting down...")

# Reference extraction function
def extract_references_from_content(content: str, pdf_chunks: list = None) -> list:
    """
    Extract reference information from AI response content
    """
    references = []

    # Find all reference markers [1], [2], etc.
    reference_pattern = r'\[(\d+)\]'
    matches = re.findall(reference_pattern, content)

    if matches and pdf_chunks:
        for match in matches:
            ref_num = int(match)
            if ref_num <= len(pdf_chunks):
                chunk = pdf_chunks[ref_num - 1]  # Index starts from 0
                reference = {
                    "id": ref_num,
                    "text": chunk.get("content", "")[:200] + "..." if len(chunk.get("content", "")) > 200 else chunk.get("content", ""),
                    "source": chunk.get("metadata", {}).get("source", "Unknown source"),
                    "page": chunk.get("metadata", {}).get("page_number", 1),
                    "chunk_id": chunk.get("metadata", {}).get("chunk_id", 0),
                    "source_info": chunk.get("metadata", {}).get("source_info", "Unknown source")
                }
                references.append(reference)

    return references

# Initialize chat model
def get_chat_model(model_name: str = None):
    """Initialize chat model"""
    if model_name is None:
        model_name = settings.default_model

    try:
        # Use latest version of ChatOpenAI
        model = ChatOpenAI(
            model=model_name,
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
    """Convert history to LangChain message format, with multimodal content support"""
    messages = []

    # Add system message
    system_prompt = """You are a professional multimodal RAG assistant with the following capabilities:
1. Document understanding and analysis
2. Image content recognition and analysis (OCR, object detection, scene understanding)
3. Audio transcription and analysis
4. Knowledge retrieval and Q&A

Important guidelines:
- When users upload images and ask questions, combine image content with the user's specific question in your answer
- Carefully analyze all visible information in images: text, charts, objects, scenes, etc.
- Focus your analysis on the parts of the image relevant to the user's question
- If the image contains text, accurately recognize and cite it in your response
- If a user uploads an image without a question, provide a comprehensive analysis of the image

Citation format requirements (important):
- When answering based on provided reference document content, you must add citation markers after relevant information in the format [1], [2], etc.
- Citation markers should immediately follow the relevant content, e.g.: "This is important information[1]"
- Use corresponding citation numbers for each different document chunk
- If the user message contains a "=== Reference Document Content ===" section, you must use that content to answer questions and add citations
- Only use superscript citations in the main text, do not list "References" at the end

Please answer in a professional, accurate, and friendly manner, and strictly follow the citation format. When reference documents are available, prioritize using document content in your answers."""

    messages.append(SystemMessage(content=system_prompt))

    # Convert history messages
    logger.info(f"Processing history messages: {len(history)} messages")
    for i, msg in enumerate(history):
        content = msg.get("content", "")
        content_blocks = msg.get("content_blocks", [])
        logger.info(f"History message {i+1}: {msg['role']}, content blocks: {len(content_blocks)}, audio transcription: {any(b.get('transcription') for b in content_blocks)}")
        
        if msg["role"] == "user":
            # If multimodal content blocks exist, build composite message
            if content_blocks:
                message_content = []

                # Add text content (if any)
                if content.strip():
                    message_content.append({
                        "type": "text",
                        "text": content
                    })

                # Process content blocks
                for block in content_blocks:
                    if block.get("type") == "text":
                        message_content.append({
                            "type": "text",
                            "text": block.get("content", "")
                        })
                    elif block.get("type") == "image":
                        # Image content block
                        image_data = block.get("content", "")
                        if image_data.startswith("data:image"):
                            message_content.append({
                                "type": "image_url",
                                "image_url": {
                                    "url": image_data
                                }
                            })
                    elif block.get("type") == "audio":
                        # Audio content block - use transcription text
                        if block.get("transcription"):
                            message_content.append({
                                "type": "text",
                                "text": f"[Audio Transcription] {block.get('transcription')}"
                            })

                messages.append(HumanMessage(content=message_content))
            else:
                # Plain text message
                messages.append(HumanMessage(content=content))

        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=content))

    return messages

def create_multimodal_message(request: MessageRequest) -> HumanMessage:
    """Create multimodal message"""
    logger.info(f"Starting to build multimodal message...")
    logger.info(f"Text content: {request.content[:100]}..." if request.content else "📝 No text content")
    logger.info(f"Content blocks count: {len(request.content_blocks)}")

    message_content = []

    # Add text content (if any)
    if request.content.strip():
        logger.info(f"Adding text content")
        message_content.append({
            "type": "text",
            "text": request.content
        })

    # Process content blocks
    for i, block in enumerate(request.content_blocks):
        logger.info(f"Processing content block {i+1}/{len(request.content_blocks)}: {block.type}")

        if block.type == "text":
            logger.info(f"Adding text block: {block.content[:50]}...")
            message_content.append({
                "type": "text",
                "text": block.content
            })
        elif block.type == "image":
            # Image content block
            if block.content.startswith("data:image"):
                logger.info(f"Adding image block, data length: {len(block.content)}")
                message_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": block.content
                    }
                })
            else:
                logger.warning(f"Invalid image data format: {block.content[:50]}...")
        elif block.type == "audio":
            # Audio content block - use transcription text directly
            if block.transcription:
                logger.info(f"Adding audio transcription text: {block.transcription[:50]}...")
                message_content.append({
                    "type": "text",
                    "text": f"[Audio Transcription] {block.transcription}"
                })
            else:
                logger.warning(f"Audio block missing transcription text")
        elif block.type == "pdf":
            # PDF content block - use filename as identifier
            logger.info(f"Adding PDF block: {block.filename}")
            message_content.append({
                "type": "text",
                "text": f"[PDF Document] {block.filename} ({(block.filesize or 0) / 1024:.1f} KB)"
            })
        else:
            logger.warning(f"Unknown content block type: {block.type}")

    logger.info(f"Message construction complete, content blocks count: {len(message_content)}")

    # If only plain text, return string directly
    if len(message_content) == 1 and message_content[0]["type"] == "text":
        logger.info(f"Returning plain text message")
        return HumanMessage(content=message_content[0]["text"])

    # Multimodal message
    logger.info(f"Returning multimodal message")
    return HumanMessage(content=message_content)

async def generate_streaming_response(
    messages: List[BaseMessage],
    model_name: str,
    pdf_chunks: List[Dict[str, Any]] = None
) -> AsyncGenerator[str, None]:
    """Generate streaming response"""
    try:
        logger.info(f"Starting streaming response generation, model: {model_name}")
        logger.info(f"Message count: {len(messages)}")

        # If PDF content exists, add it to system message
        if pdf_chunks and len(pdf_chunks) > 0:
            logger.info(f"Detected {len(pdf_chunks)} PDF chunks, adding to context")
            pdf_content = "\n\n=== Reference Document Content ===\n"
            for i, chunk in enumerate(pdf_chunks, 1):
                content = chunk.get("content", "")[:500]  # Limit length
                source_info = chunk.get("metadata", {}).get("source_info", f"Document chunk {i}")
                pdf_content += f"\n[{i}] {content}\nSource: {source_info}\n"

            pdf_content += "\nPlease cite relevant content in your answer using formats like [1], [2], etc.\n"

            # Add PDF content to the last user message
            if messages and isinstance(messages[-1], HumanMessage):
                if isinstance(messages[-1].content, str):
                    messages[-1].content = messages[-1].content + pdf_content
                    logger.info(f"Added PDF content to user message, total length: {len(messages[-1].content)}")
                elif isinstance(messages[-1].content, list):
                    messages[-1].content.append({"type": "text", "text": pdf_content})
                    logger.info(f"Added PDF content as new block to user message")

        # Log each message type
        for i, msg in enumerate(messages):
            if hasattr(msg, 'content'):
                if isinstance(msg.content, str):
                    logger.info(f"Message {i+1}: {type(msg).__name__} - Plain text, length: {len(msg.content)}")
                elif isinstance(msg.content, list):
                    logger.info(f"Message {i+1}: {type(msg).__name__} - Multimodal, block count: {len(msg.content)}")
                    for j, block in enumerate(msg.content):
                        if isinstance(block, dict):
                            logger.info(f"   Block {j+1}: {block.get('type', 'unknown')}")

        model = get_chat_model(model_name)
        logger.info(f"Model initialization complete")

        # Create streaming response
        full_response = ""
        logger.info(f"Starting streaming generation...")

        chunk_count = 0
        async for chunk in model.astream(messages):
            chunk_count += 1
            logger.debug(f"Received chunk {chunk_count}")
            if hasattr(chunk, 'content') and chunk.content:
                content = chunk.content
                full_response += content

                # Send each chunk's content directly, avoid duplication
                data = {
                    "type": "content_delta",
                    "content": content,
                    "timestamp": datetime.now().isoformat()
                }
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


        # Extract reference information
        references = extract_references_from_content(full_response, pdf_chunks) if pdf_chunks else []
        logger.info(f"Extracted {len(references)} references")

        # Send completion signal
        final_data = {
            "type": "message_complete",
            "full_content": full_response,
            "timestamp": datetime.now().isoformat(),
            "references": references
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

@app.options("/api/chat/stream")
async def chat_stream_options():
    """Handle CORS preflight for streaming endpoint"""
    return {"status": "ok"}

@app.post("/api/chat/stream")
async def chat_stream(request: MessageRequest):
    """Streaming chat endpoint (multimodal support)"""
    try:
        # Log request information
        has_images = any(block.type == "image" for block in request.content_blocks)
        content_preview = request.content[:100] if request.content else "Multimodal message"
        logger.info(f"Received chat request: {content_preview}... (includes images: {has_images})")

        # PDF chunks reception status
        logger.info(f"Received PDF chunks count: {len(request.pdf_chunks) if request.pdf_chunks else 0}")
        if request.pdf_chunks:
            logger.info(f"PDF chunks preview: {str(request.pdf_chunks[:2])[:200]}...")
        else:
            logger.info(f"PDF chunks empty or None: {request.pdf_chunks}")

        # Convert message history
        messages = convert_history_to_messages(request.history)

        # Add current user message (multimodal support)
        current_message = create_multimodal_message(request)
        messages.append(current_message)

        # Return streaming response
        return StreamingResponse(
            generate_streaming_response(messages, request.model, request.pdf_chunks),
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

@app.options("/api/chat")
async def chat_sync_options():
    """Handle CORS preflight for sync chat endpoint"""
    return {"status": "ok"}

@app.post("/api/chat")
async def chat_sync(request: MessageRequest):
    """Synchronous chat endpoint (multimodal support)"""
    try:
        # Log request information
        has_images = any(block.type == "image" for block in request.content_blocks)
        content_preview = request.content[:100] if request.content else "Multimodal message"
        logger.info(f"Received synchronous chat request: {content_preview}... (includes images: {has_images})")

        # Convert message history
        messages = convert_history_to_messages(request.history)

        # Add current user message (multimodal support)
        current_message = create_multimodal_message(request)
        messages.append(current_message)

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
                "description": "Next-generation GPT model (if available)"
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

@app.options("/api/pdf/process")
async def process_pdf_stream_options():
    """Handle CORS preflight for PDF processing endpoint"""
    return {"status": "ok"}

@app.post("/api/pdf/process")
async def process_pdf_stream(file_data: Dict[str, Any]):
    """
    Stream PDF document processing
    """
    try:
        # Extract request data
        content = file_data.get("content", "")  # base64-encoded PDF content
        filename = file_data.get("filename", "document.pdf")

        if not content:
            raise HTTPException(status_code=400, detail="Missing PDF content")

        # Decode base64 data
        import base64
        try:
            # Check for data URL prefix
            if content.startswith('data:'):
                # Has data URL prefix (data:application/pdf;base64,...)
                pdf_bytes = base64.b64decode(content.split(',')[-1])
            else:
                # Pure base64 data
                pdf_bytes = base64.b64decode(content)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"PDF data decode failed: {str(e)}")

        # Validate file size (50MB limit)
        max_size = 50 * 1024 * 1024  # 50MB
        if len(pdf_bytes) > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"PDF file too large: {len(pdf_bytes) / 1024 / 1024:.1f}MB, maximum supported is 50MB"
            )

        logger.info(f"Starting PDF processing: {filename}, size: {len(pdf_bytes)} bytes")

        # Define streaming response generator
        async def generate_pdf_stream():
            try:
                async for chunk in pdf_processor.process_pdf_stream(pdf_bytes, filename):
                    chunk_data = json.dumps(chunk, ensure_ascii=False)
                    yield f"data: {chunk_data}\n\n"

                    # If error, terminate immediately
                    if chunk.get("type") == "error":
                        break

            except Exception as e:
                logger.error(f"PDF streaming processing failed: {str(e)}")
                error_chunk = json.dumps({
                    "type": "error",
                    "error": f"Error occurred during processing: {str(e)}"
                }, ensure_ascii=False)
                yield f"data: {error_chunk}\n\n"

            yield "data: [DONE]\n\n"

        return StreamingResponse(
            generate_pdf_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                # CORS handled by CORSMiddleware, no need to set manually
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF processing endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/pdf/pages")
async def extract_pdf_pages(file_data: Dict[str, Any]):
    """
    Extract PDF pages as images (for multimodal processing)
    """
    try:
        content = file_data.get("content", "")
        max_pages = file_data.get("max_pages", 3)

        if not content:
            raise HTTPException(status_code=400, detail="Missing PDF content")

        # Decode PDF data
        import base64
        try:
            pdf_bytes = base64.b64decode(content.split(',')[-1])
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"PDF data decode failed: {str(e)}")

        logger.info(f"Extracting PDF page images, max {max_pages} pages")

        # Extract page images
        page_images = await pdf_processor.extract_pdf_pages_as_images(pdf_bytes, max_pages)

        return {
            "success": True,
            "total_pages": len(page_images),
            "images": page_images
        }

    except Exception as e:
        logger.error(f"PDF page extraction failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ================================
# Audio processing endpoints
# ================================

@app.post("/api/audio/process")
async def process_audio(file: UploadFile = File(...)):
    """Process audio file for speech-to-text transcription"""

    if not audio_processor:
        raise HTTPException(status_code=500, detail="Audio processor not initialized, please check dependencies")

    try:
        logger.info(f"🎙️ Starting audio processing: {file.filename}")

        # Check file type
        allowed_types = {
            'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/flac', 'audio/m4a', 'audio/ogg',
            'video/mp4', 'video/avi', 'video/mov', 'video/mkv', 'video/webm'
        }

        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")

        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        try:
            # Process audio
            result = audio_processor.process_audio_file(temp_file_path, file.filename)

            logger.info(f"Audio processing successful: {file.filename}")
            return {
                "success": True,
                "filename": result["filename"],
                "transcription": result["transcription"],
                "duration": result["duration"],
                "format": result["format"]
            }

        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    except Exception as e:
        logger.error(f"Audio processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Audio processing failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host=settings.host, 
        port=settings.port,
        log_level=settings.log_level.lower()
    ) 