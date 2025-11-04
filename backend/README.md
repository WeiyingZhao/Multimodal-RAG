# Multimodal RAG Workbench - Backend API

Intelligent conversation backend service based on LangChain 1.0, supporting the latest models including GPT-5.

## 🖥️ User Interface

![Multimodal RAG Workbench UI](../multi_rag_ocr_ui.png)

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure API Key

Modify the OpenAI API Key in the `env_config.py` file:

```python
os.environ["OPENAI_API_KEY"] = "your_actual_api_key_here"
```

### 3. Start the Service

```bash
python start.py
```

The service will start at `http://localhost:8000`

## 📚 API Endpoints

### Streaming Chat Endpoint
- **URL**: `POST /api/chat/stream`
- **Content-Type**: `application/json`
- **Response**: `text/event-stream`

```json
{
  "content": "Hello",
  "history": [],
  "model": "gpt-4o",
  "knowledge_base": "default"
}
```

### Synchronous Chat Endpoint
- **URL**: `POST /api/chat`
- **Content-Type**: `application/json`

### Health Check
- **URL**: `GET /`

### Model List
- **URL**: `GET /api/models`

### Knowledge Base List
- **URL**: `GET /api/knowledge-bases`

## 🧪 Testing

Run the test client:

```bash
python test_client.py
```

## 📖 API Documentation

Visit `http://localhost:8000/docs` to view the interactive API documentation.

## 🔧 Configuration

### Supported Models
- `gpt-4o` - GPT-4 optimized version
- `gpt-4o-mini` - Lightweight version
- `gpt-5` - Next-generation model (if available)

### Environment Variables
- `OPENAI_API_KEY` - OpenAI API key
- `OPENAI_BASE_URL` - API base URL
- `HOST` - Server host
- `PORT` - Server port
- `DEBUG` - Debug mode
- `LOG_LEVEL` - Log level

## 🔗 Frontend Integration

The frontend communicates with the backend through `src/api/chat.ts`, supporting:
- Streaming text responses
- Conversation history management
- Error handling
- Model switching 