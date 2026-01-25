"""Core module initialization"""
from .document_processor import DocumentProcessor, ProcessedDocument, process_document
from .embeddings import (
    BaseEmbeddingService, 
    OpenAIEmbeddingService, 
    HuggingFaceEmbeddingService,
    get_embedding_service,
    cosine_similarity
)
from .vector_store import VectorStore, SearchResult, SearchResults, get_vector_store
from .query_engine import QueryEngine, QueryResponse, Citation, get_query_engine

__all__ = [
    # Document Processing
    "DocumentProcessor",
    "ProcessedDocument", 
    "process_document",
    
    # Embeddings
    "BaseEmbeddingService",
    "OpenAIEmbeddingService",
    "HuggingFaceEmbeddingService",
    "get_embedding_service",
    "cosine_similarity",
    
    # Vector Store
    "VectorStore",
    "SearchResult",
    "SearchResults",
    "get_vector_store",
    
    # Query Engine
    "QueryEngine",
    "QueryResponse",
    "Citation",
    "get_query_engine"
]
