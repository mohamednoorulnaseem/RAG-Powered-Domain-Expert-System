"""
RAG Expert System - Embedding Service
Handles vector embedding generation using OpenAI or HuggingFace models
"""

from typing import List, Optional
import numpy as np
from abc import ABC, abstractmethod

from openai import OpenAI
from sentence_transformers import SentenceTransformer
from langchain_core.documents import Document
from loguru import logger

from config import get_settings


class BaseEmbeddingService(ABC):
    """Abstract base class for embedding services"""

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        pass

    @abstractmethod
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        pass

    @abstractmethod
    def embed_documents(self, documents: List[Document]) -> List[List[float]]:
        """Generate embeddings for document chunks"""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return embedding dimension"""
        pass


class OpenAIEmbeddingService(BaseEmbeddingService):
    """
    OpenAI Embedding Service

    Uses OpenAI's text-embedding-3-large model (1536 dimensions)
    - High quality embeddings
    - Semantic understanding
    - ~$0.0001 per 1K tokens
    """

    DIMENSION_MAP = {
        "text-embedding-3-large": 3072,
        "text-embedding-3-small": 1536,
        "text-embedding-ada-002": 1536,
    }

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None):
        self.settings = get_settings()
        self.model = model or self.settings.embedding_model
        self._api_key = api_key or self.settings.openai_api_key
        self._client = None
        self._dimension = self.DIMENSION_MAP.get(self.model, 1536)

        logger.info(f"OpenAI Embedding Service initialized with model: {self.model}")

    @property
    def client(self):
        if self._client is None:
            api_key = self._api_key
            if not api_key or "your-api-key" in api_key:
                api_key = "mock_key_for_testing"
            self._client = OpenAI(api_key=api_key)
        return self._client

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        response = self.client.embeddings.create(model=self.model, input=text)
        return response.data[0].embedding

    def embed_texts(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """
        Generate embeddings for multiple texts
        Uses batching to handle large numbers of texts
        """
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]

            response = self.client.embeddings.create(model=self.model, input=batch)

            # Sort by index to maintain order
            batch_embeddings = sorted(response.data, key=lambda x: x.index)
            all_embeddings.extend([e.embedding for e in batch_embeddings])

            logger.debug(f"Embedded batch {i // batch_size + 1}: {len(batch)} texts")

        logger.info(f"Generated {len(all_embeddings)} embeddings using OpenAI")
        return all_embeddings

    def embed_documents(self, documents: List[Document]) -> List[List[float]]:
        """Generate embeddings for document chunks"""
        texts = [doc.page_content for doc in documents]
        return self.embed_texts(texts)


class HuggingFaceEmbeddingService(BaseEmbeddingService):
    """
    HuggingFace Embedding Service (Local, Free)

    Uses sentence-transformers models locally
    - No API costs
    - Runs on your machine
    - Good for privacy-sensitive data
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self._dimension = self.model.get_sentence_embedding_dimension()

        logger.info(
            f"HuggingFace Embedding Service initialized with model: {model_name}"
        )

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        logger.info(f"Generated {len(texts)} embeddings using HuggingFace")
        return embeddings.tolist()

    def embed_documents(self, documents: List[Document]) -> List[List[float]]:
        """Generate embeddings for document chunks"""
        texts = [doc.page_content for doc in documents]
        return self.embed_texts(texts)


def get_embedding_service(use_openai: bool = True) -> BaseEmbeddingService:
    """
    Factory function to get embedding service

    Args:
        use_openai: If True, use OpenAI (better quality, costs money)
                   If False, use HuggingFace (free, runs locally)
    """
    if use_openai:
        return OpenAIEmbeddingService()
    else:
        return HuggingFaceEmbeddingService()


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors

    Cosine similarity = (A · B) / (||A|| × ||B||)

    Result range: -1 to 1
    - 1 = identical
    - 0 = orthogonal (no similarity)
    - -1 = opposite
    """
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)

    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return float(dot_product / (norm1 * norm2))
