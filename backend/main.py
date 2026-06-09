"""
main.py — FastAPI Application

Provides the REST API for the RAG-Powered Domain Expert System:
- Document upload, listing, and deletion
- Chat (synchronous and streaming via SSE)
- Conversation history management
- Health check

All endpoints handle errors gracefully and return structured JSON responses.
"""

import os
import uuid
import json
import logging
from typing import Optional, Dict, List
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from rag_pipeline import RAGPipeline

# Load environment variables from .env file
load_dotenv()

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
DEFAULT_CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
DEFAULT_CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")

# Ensure upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# FastAPI App Initialization
# ──────────────────────────────────────────────

app = FastAPI(
    title="RAG-Powered Domain Expert System",
    description="Upload documents and ask questions — answers grounded in your data.",
    version="1.0.0",
)

# CORS — allow the React frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────
# Global State
# ──────────────────────────────────────────────

# The RAG pipeline instance — shared across all requests
rag_pipeline = RAGPipeline()

# In-memory conversation history, keyed by session_id
# In production, you'd use Redis or a database
conversation_history: Dict[str, List[Dict]] = {}

# ──────────────────────────────────────────────
# Request/Response Models
# ──────────────────────────────────────────────


class ChatRequest(BaseModel):
    """Incoming chat message from the frontend."""
    message: str
    session_id: str = "default"
    api_key: Optional[str] = None
    model: str = "gpt-4o"
    top_k: int = 5
    temperature: float = 0.1
    chunk_size: int = DEFAULT_CHUNK_SIZE
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP


class ChatResponse(BaseModel):
    """Response from the RAG pipeline."""
    answer: str
    sources: list
    session_id: str


class DocumentResponse(BaseModel):
    """Metadata for an uploaded document."""
    id: str
    filename: str
    chunk_count: int
    file_size: int
    status: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    documents_loaded: int
    timestamp: str


# ──────────────────────────────────────────────
# Helper Functions
# ──────────────────────────────────────────────


def get_api_key(provided_key: Optional[str] = None) -> str:
    """
    Resolve the OpenAI API key: prefer the user-provided key,
    fall back to the environment variable.
    """
    key = provided_key or os.getenv("OPENAI_API_KEY", "")
    if not key:
        raise HTTPException(
            status_code=400,
            detail="OpenAI API key is required. Set it in the Settings panel or as the OPENAI_API_KEY environment variable.",
        )
    return key


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check — returns server status and document count."""
    return HealthResponse(
        status="healthy",
        documents_loaded=len(rag_pipeline.get_documents()),
        timestamp=datetime.utcnow().isoformat(),
    )


@app.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    api_key: Optional[str] = Form(None),
    chunk_size: int = Form(DEFAULT_CHUNK_SIZE),
    chunk_overlap: int = Form(DEFAULT_CHUNK_OVERLAP),
):
    """
    Upload a document (PDF, TXT, or DOCX), process it, and add to the FAISS index.

    The file is saved to disk, loaded via LangChain, chunked, embedded, and indexed.
    Returns metadata about the processed document.
    """
    # Validate file extension
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")

    from document_processor import DocumentProcessor
    if not DocumentProcessor.is_supported(file.filename):
        supported = ", ".join(DocumentProcessor.supported_extensions())
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type. Supported formats: {supported}",
        )

    # Read file content and check size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE_MB}MB.",
        )

    # Save to disk with a unique name to avoid collisions
    doc_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1]
    saved_filename = f"{doc_id}{ext}"
    file_path = os.path.join(UPLOAD_DIR, saved_filename)

    with open(file_path, "wb") as f:
        f.write(content)

    logger.info(f"File saved: {file.filename} → {saved_filename} ({len(content)} bytes)")

    # Process and index the document
    try:
        resolved_key = get_api_key(api_key)
        result = rag_pipeline.add_document(
            file_path=file_path,
            doc_id=doc_id,
            original_filename=file.filename,
            api_key=resolved_key,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        return DocumentResponse(**result)

    except ValueError as e:
        # Clean up the saved file on processing failure
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        logger.error(f"Document processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")


@app.get("/documents", response_model=List[DocumentResponse])
async def list_documents():
    """List all uploaded and indexed documents."""
    docs = rag_pipeline.get_documents()
    return [DocumentResponse(**doc) for doc in docs]


@app.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    api_key: Optional[str] = Query(None),
):
    """
    Delete a document and remove its vectors from the FAISS index.

    The index is rebuilt from remaining documents to ensure consistency.
    """
    resolved_key = get_api_key(api_key)

    # Remove file from disk
    for fname in os.listdir(UPLOAD_DIR):
        if fname.startswith(doc_id):
            file_path = os.path.join(UPLOAD_DIR, fname)
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Deleted file: {file_path}")
            break

    # Remove from the pipeline (rebuilds FAISS index)
    removed = rag_pipeline.remove_document(doc_id, resolved_key)

    if not removed:
        raise HTTPException(status_code=404, detail="Document not found.")

    return {"status": "deleted", "doc_id": doc_id}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message and get a RAG-grounded answer (non-streaming).

    Maintains conversation history per session for context.
    """
    resolved_key = get_api_key(request.api_key)

    # Store user message in history
    if request.session_id not in conversation_history:
        conversation_history[request.session_id] = []

    conversation_history[request.session_id].append({
        "role": "user",
        "content": request.message,
        "timestamp": datetime.utcnow().isoformat(),
    })

    try:
        result = rag_pipeline.query(
            question=request.message,
            api_key=resolved_key,
            model=request.model,
            top_k=request.top_k,
            temperature=request.temperature,
        )

        # Store AI response in history
        conversation_history[request.session_id].append({
            "role": "assistant",
            "content": result["answer"],
            "sources": result["sources"],
            "timestamp": datetime.utcnow().isoformat(),
        })

        return ChatResponse(
            answer=result["answer"],
            sources=result["sources"],
            session_id=request.session_id,
        )

    except Exception as e:
        logger.error(f"Chat query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Send a message and stream the RAG-grounded answer via Server-Sent Events (SSE).

    Each event is a JSON object with type "token", "done", or "error".
    This enables real-time, word-by-word display in the frontend.
    """
    resolved_key = get_api_key(request.api_key)

    # Store user message in history
    if request.session_id not in conversation_history:
        conversation_history[request.session_id] = []

    conversation_history[request.session_id].append({
        "role": "user",
        "content": request.message,
        "timestamp": datetime.utcnow().isoformat(),
    })

    async def event_generator():
        full_response = ""
        sources = []

        try:
            async for chunk in rag_pipeline.query_stream(
                question=request.message,
                api_key=resolved_key,
                model=request.model,
                top_k=request.top_k,
                temperature=request.temperature,
            ):
                if chunk["type"] == "token":
                    full_response += chunk["content"]
                    yield f"data: {json.dumps(chunk)}\n\n"

                elif chunk["type"] == "done":
                    sources = chunk.get("sources", [])
                    yield f"data: {json.dumps(chunk)}\n\n"

                elif chunk["type"] == "error":
                    yield f"data: {json.dumps(chunk)}\n\n"

            # Store complete response in conversation history
            conversation_history[request.session_id].append({
                "role": "assistant",
                "content": full_response,
                "sources": sources,
                "timestamp": datetime.utcnow().isoformat(),
            })

        except Exception as e:
            logger.error(f"Streaming failed: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@app.delete("/chat/history")
async def clear_chat_history(session_id: str = Query("default")):
    """Clear conversation history for a session."""
    if session_id in conversation_history:
        del conversation_history[session_id]

    return {"status": "cleared", "session_id": session_id}


@app.get("/chat/history")
async def get_chat_history(session_id: str = Query("default")):
    """Get conversation history for a session."""
    history = conversation_history.get(session_id, [])
    return {"session_id": session_id, "messages": history}


# ──────────────────────────────────────────────
# Run with: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
