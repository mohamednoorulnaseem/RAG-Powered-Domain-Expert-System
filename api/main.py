"""
RAG Expert System - FastAPI Backend
REST API for document management and querying
"""

import os
import shutil
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from fastapi import FastAPI, File, UploadFile, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from loguru import logger

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_settings
from core import (
    DocumentProcessor,
    VectorStore,
    QueryEngine,
    get_query_engine
)

# Configure logging
try:
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    logger.add("logs/api.log", rotation="10 MB", level="DEBUG")
    logger.info("API Logging configured")
except Exception as e:
    print(f"Failed to configure logging: {e}")


# ========================================
# Pydantic Models
# ========================================

class QueryRequest(BaseModel):
    """Request model for queries"""
    question: str = Field(..., min_length=1, max_length=2000)
    top_k: Optional[int] = Field(5, ge=1, le=20)
    min_score: Optional[float] = Field(0.5, ge=0.0, le=1.0)
    session_id: Optional[str] = Field(None, description="Unique session ID for conversation memory")
    hybrid_weight: Optional[float] = Field(0.5, ge=0.0, le=1.0, description="Weight for vector vs keyword search")


class QueryResponseModel(BaseModel):
    """Response model for queries"""
    query: str
    answer: str
    citations: List[dict]
    confidence: str
    metrics: dict


class DocumentInfo(BaseModel):
    """Document information model"""
    doc_id: str
    source: str
    file_type: str
    chunks: int


class StatsResponse(BaseModel):
    """System statistics response"""
    total_chunks: int
    total_documents: int
    collection_name: str
    documents: List[DocumentInfo]


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: str
    version: str
    components: dict


# ========================================
# App Initialization
# ========================================

app = FastAPI(
    title="RAG Expert System API",
    description="""
    🚀 **RAG (Retrieval-Augmented Generation) Expert System**
    
    Upload documents and ask questions to get accurate, source-cited answers.
    
    ## Features
    - 📄 Upload PDF, DOCX, TXT, MD documents
    - 🔍 Semantic search with vector embeddings
    - 💬 AI-powered answers with citations
    - 📊 Confidence scoring and metrics
    
    ## How it Works
    1. **Upload** documents to the system
    2. Documents are **chunked and embedded**
    3. **Ask questions** in natural language
    4. Get **accurate answers** with source citations
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
settings = get_settings()
document_processor = DocumentProcessor()
vector_store = VectorStore()
query_engine = QueryEngine(vector_store=vector_store)


# ========================================
# Helper Functions
# ========================================

async def save_upload_file(upload_file: UploadFile) -> Path:
    """Save uploaded file to disk"""
    upload_dir = settings.upload_dir
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{upload_file.filename}"
    file_path = upload_dir / filename
    
    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    
    return file_path


# ========================================
# API Endpoints
# ========================================

@app.get("/", tags=["General"])
async def root():
    """Root endpoint with API information"""
    return {
        "name": "RAG Expert System API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }


@app.get("/health", response_model=HealthResponse, tags=["General"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "components": {
            "api": "online",
            "vector_store": "online",
            "documents_indexed": vector_store.collection.count()
        }
    }


@app.post("/documents/upload", tags=["Documents"])
async def upload_document(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    Upload a document for processing
    
    Supported formats: PDF, DOCX, TXT, MD
    
    The document will be:
    1. Saved to disk
    2. Parsed and chunked
    3. Embedded and stored in vector database
    """
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Supported: {settings.allowed_extensions}"
        )
    
    try:
        # Save file
        file_path = await save_upload_file(file)
        logger.info(f"File saved: {file_path}")
        
        # Process document
        processed_doc = document_processor.process_document(str(file_path))
        
        # Add to vector store
        logger.debug(f"Adding {processed_doc.num_chunks} chunks to vector store...")
        result = vector_store.add_documents(processed_doc.chunks)
        logger.debug(f"Add result: {result}")
        
        return {
            "success": True,
            "document": {
                "doc_id": processed_doc.doc_id,
                "filename": processed_doc.filename,
                "file_type": processed_doc.file_type,
                "pages": processed_doc.num_pages,
                "chunks": processed_doc.num_chunks
            },
            "indexing": result
        }
        
    except Exception as e:
        with open("debug_error.log", "a") as f:
            f.write(f"Upload Error: {e}\n")
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    # Explicitly debug successful path
    with open("debug_upload.log", "a") as f:
         f.write(f"Success! Added {len(processed_doc.chunks)} chunks. Persistence path: {vector_store.persist_path}\n")


@app.post("/documents/upload-multiple", tags=["Documents"])
async def upload_multiple_documents(files: List[UploadFile] = File(...)):
    """Upload multiple documents at once"""
    results = []
    errors = []
    
    for file in files:
        try:
            file_ext = Path(file.filename).suffix.lower()
            if file_ext not in settings.allowed_extensions:
                errors.append({
                    "filename": file.filename,
                    "error": f"Unsupported file type: {file_ext}"
                })
                continue
            
            file_path = await save_upload_file(file)
            processed_doc = document_processor.process_document(str(file_path))
            vector_store.add_documents(processed_doc.chunks)
            
            results.append({
                "doc_id": processed_doc.doc_id,
                "filename": processed_doc.filename,
                "chunks": processed_doc.num_chunks
            })
            
        except Exception as e:
            errors.append({
                "filename": file.filename,
                "error": str(e)
            })
    
    return {
        "success": len(results) > 0,
        "processed": len(results),
        "failed": len(errors),
        "documents": results,
        "errors": errors
    }


@app.get("/documents", tags=["Documents"])
async def list_documents():
    """List all indexed documents"""
    documents = vector_store.list_documents()
    return {
        "total": len(documents),
        "documents": documents
    }


@app.get("/documents/{doc_id}", tags=["Documents"])
async def get_document(doc_id: str):
    """Get details for a specific document"""
    chunks = vector_store.get_document_chunks(doc_id)
    
    if not chunks:
        raise HTTPException(status_code=404, detail=f"Document not found: {doc_id}")
    
    return {
        "doc_id": doc_id,
        "source": chunks[0].metadata.get('source', 'Unknown'),
        "num_chunks": len(chunks),
        "chunks": [
            {
                "chunk_id": c.chunk_id,
                "page": c.metadata.get('page', 0),
                "content_preview": c.content[:200] + "..." if len(c.content) > 200 else c.content
            }
            for c in chunks[:10]  # Limit to first 10 chunks
        ]
    }


@app.delete("/documents/{doc_id}", tags=["Documents"])
async def delete_document(doc_id: str):
    """Delete a document from the system"""
    result = vector_store.delete_document(doc_id)
    
    if result['deleted'] == 0:
        raise HTTPException(status_code=404, detail=f"Document not found: {doc_id}")
    
    return {
        "success": True,
        "deleted_chunks": result['deleted'],
        "doc_id": doc_id
    }


@app.post("/query", response_model=QueryResponseModel, tags=["Query"])
async def query_documents(request: QueryRequest):
    """
    Ask a question about your documents
    
    The system will:
    1. Search for relevant document chunks
    2. Generate an answer using GPT-4
    3. Provide citations and confidence score
    """
    try:
        response = query_engine.query(
            question=request.question,
            top_k=request.top_k,
            min_score=request.min_score,
            session_id=request.session_id,
            hybrid_weight=request.hybrid_weight
        )
        
        return response.to_dict()
        
    except Exception as e:
        logger.error(f"Query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/search", tags=["Query"])
async def search_chunks(
    q: str = Query(..., min_length=1, description="Search query"),
    top_k: int = Query(5, ge=1, le=20, description="Number of results")
):
    """
    Search for relevant chunks (without generating an answer)
    
    Useful for debugging or exploring what's in the vector store.
    """
    results = query_engine.get_similar_chunks(query=q, top_k=top_k)
    return {
        "query": q,
        "results": results
    }


@app.get("/documents/{doc_id}/summary", tags=["Documents"])
async def summarize_document(doc_id: str):
    """Generate a summary of a specific document"""
    try:
        result = query_engine.summarize_document(doc_id)
        
        if 'error' in result:
            raise HTTPException(status_code=404, detail=result['error'])
        
        return result
        
    except Exception as e:
        logger.error(f"Summary error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats", response_model=StatsResponse, tags=["General"])
async def get_stats():
    """Get system statistics"""
    stats = vector_store.get_stats()
    return stats


@app.post("/admin/reindex", tags=["Admin"])
async def reindex_documents(background_tasks: BackgroundTasks):
    """Re-index all files in the uploads directory"""
    try:
        count = 0
        errors = []
        upload_dir = settings.upload_dir
        
        # Get all files
        files = []
        for ext in settings.allowed_extensions:
            files.extend(list(upload_dir.glob(f"*{ext}")))
            
        logger.info(f"Found {len(files)} files to re-index")
        
        for file_path in files:
            try:
                processed_doc = document_processor.process_document(str(file_path))
                vector_store.add_documents(processed_doc.chunks)
                count += 1
            except Exception as e:
                logger.error(f"Failed to re-index {file_path.name}: {e}")
                errors.append(f"{file_path.name}: {e}")
                
        return {
            "success": True,
            "reindexed": count,
            "total_found": len(files),
            "errors": errors
        }
    except Exception as e:
        logger.error(f"Re-indexing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========================================
# Error Handlers
# ========================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again."}
    )


# ========================================
# Run Configuration
# ========================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
