"""
RAG Expert System - Configuration Settings
Centralized configuration management with environment variable support
"""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # ========================================
    # API Configuration
    # ========================================
    openai_api_key: str = ""
    together_api_key: str = ""
    
    # ========================================
    # Model Configuration
    # ========================================
    embedding_model: str = "text-embedding-3-large"
    llm_model: str = "gpt-4-turbo-preview"
    temperature: float = 0.0  # Deterministic responses
    max_tokens: int = 2000
    
    # ========================================
    # Document Processing
    # ========================================
    chunk_size: int = 1000
    chunk_overlap: int = 200
    max_file_size_mb: int = 50
    allowed_extensions: list = [".pdf", ".docx", ".txt", ".md"]
    
    # ========================================
    # Vector Database
    # ========================================
    chroma_persist_directory: str = "./data/chroma_db"
    collection_name: str = "documents"
    
    # ========================================
    # Search Configuration
    # ========================================
    top_k_results: int = 5
    similarity_threshold: float = 0.7
    
    # ========================================
    # Caching
    # ========================================
    redis_url: Optional[str] = None
    cache_ttl_seconds: int = 3600  # 1 hour
    
    # ========================================
    # Server Configuration
    # ========================================
    api_host: str = "0.0.0.0"
    api_port: int = 8001
    streamlit_port: int = 8501
    debug: bool = False
    
    # ========================================
    # Paths
    # ========================================
    base_dir: Path = Path(__file__).parent.parent
    upload_dir: Path = base_dir / "uploads"
    data_dir: Path = base_dir / "data"
    logs_dir: Path = base_dir / "logs"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"
    
    def ensure_directories(self):
        """Create necessary directories if they don't exist"""
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        Path(self.chroma_persist_directory).mkdir(parents=True, exist_ok=True)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    settings = Settings()
    settings.ensure_directories()
    return settings


# ========================================
# Prompt Templates
# ========================================

SYSTEM_PROMPT = """You are an expert document analyst assistant. Your role is to provide accurate, 
comprehensive answers based ONLY on the provided context from uploaded documents.

Key Guidelines:
1. Only use information explicitly stated in the context
2. If the answer is not in the context, clearly state: "I cannot find this information in the provided documents"
3. Always cite your sources with specific document names and relevant quotes
4. Be precise, professional, and thorough
5. If asked about topics outside the documents, politely redirect to document-related queries
6. Format your responses with clear structure when appropriate"""

QUERY_PROMPT_TEMPLATE = """Based on the following context from uploaded documents, please answer the question.

CONTEXT:
{context}

QUESTION: {question}

INSTRUCTIONS:
- Answer based ONLY on the context provided above
- If the answer is not in the context, say "I cannot find this information in the provided documents"
- Cite specific sources when possible
- Be precise and comprehensive

ANSWER:"""

SUMMARY_PROMPT_TEMPLATE = """Please provide a comprehensive summary of the following document content:

CONTENT:
{content}

Provide a summary that includes:
1. Main topics covered
2. Key points and findings
3. Important details and figures
4. Overall document purpose

SUMMARY:"""
