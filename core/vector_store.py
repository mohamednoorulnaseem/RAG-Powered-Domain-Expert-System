"""
RAG Expert System - Vector Store
Simple in-memory vector store with persistence using pickle
Works without ChromaDB for Python 3.14 compatibility
"""

import os
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

import numpy as np
from langchain_core.documents import Document
from loguru import logger
from rank_bm25 import BM25Okapi
import re

from config import get_settings
from core.embeddings import (
    get_embedding_service,
    BaseEmbeddingService,
    cosine_similarity,
)


@dataclass
class SearchResult:
    """Represents a single search result"""

    chunk_id: str
    content: str
    score: float  # Similarity score (0-1)
    metadata: Dict[str, Any]

    @property
    def source(self) -> str:
        return self.metadata.get("source", "Unknown")

    @property
    def page(self) -> int:
        return self.metadata.get("page", 0)


@dataclass
class SearchResults:
    """Collection of search results with metadata"""

    query: str
    results: List[SearchResult]
    search_time_ms: float
    total_documents: int

    @property
    def has_results(self) -> bool:
        return len(self.results) > 0

    @property
    def best_score(self) -> float:
        return self.results[0].score if self.results else 0.0


@dataclass
class VectorEntry:
    """A single entry in the vector store"""

    chunk_id: str
    embedding: List[float]
    text: str
    metadata: Dict[str, Any]


class VectorStore:
    """
    Simple In-Memory Vector Store with Persistence

    Uses numpy for similarity calculations and pickle for persistence.
    Works without ChromaDB dependencies.
    """

    def __init__(
        self,
        embedding_service: Optional[BaseEmbeddingService] = None,
        persist_path: Optional[str] = None,
    ):

        self.settings = get_settings()
        self.persist_path = persist_path or str(
            self.settings.data_dir / "vector_store.json"
        )  # Changed to JSON

        # Initialize embedding service
        self.embedding_service = embedding_service or get_embedding_service(
            use_openai=True
        )

        # In-memory storage
        self.entries: List[VectorEntry] = []
        self.bm25: Optional[BM25Okapi] = None

        # Load from disk if exists
        self._load()
        self._init_bm25()

        logger.info(f"VectorStore initialized. Entries: {len(self.entries)}")

    def _save(self):
        """Save vector store to disk (JSON)"""
        try:
            Path(self.persist_path).parent.mkdir(parents=True, exist_ok=True)

            # Convert entries to dicts
            data = [asdict(e) for e in self.entries]

            with open(self.persist_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Saved {len(self.entries)} entries to {self.persist_path}")
            print(
                f"DEBUG: Saved {len(self.entries)} entries to {self.persist_path}"
            )  # Console visible
        except Exception as e:
            logger.error(f"Failed to save vector store: {e}")
            print(f"DEBUG: Failed to save: {e}")

    def _load(self):
        """Load vector store from disk (JSON)"""
        if os.path.exists(self.persist_path):
            try:
                with open(self.persist_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Reconstruct VectorEntry objects
                self.entries = [VectorEntry(**item) for item in data]

                logger.info(f"Loaded {len(self.entries)} entries from disk")
                print(f"DEBUG: Loaded {len(self.entries)} entries from disk")
            except Exception as e:
                logger.warning(f"Could not load vector store: {e}")
                print(f"DEBUG: Load failed: {e}")
                self.entries = []

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenizer for BM25"""
        return re.findall(r"\w+", text.lower())

    def _init_bm25(self):
        """Initialize BM25 index for keyword search"""
        if not self.entries:
            self.bm25 = None
            return

        corpus = [self._tokenize(entry.text) for entry in self.entries]
        self.bm25 = BM25Okapi(corpus)
        logger.debug(f"BM25 index initialized with {len(self.entries)} entries")

    @property
    def collection(self):
        """Compatibility property for count()"""

        class _Collection:
            def __init__(self, entries):
                self._entries = entries

            def count(self):
                return len(self._entries)

        return _Collection(self.entries)

    def add_documents(self, documents: List[Document]) -> Dict[str, Any]:
        """
        Add documents to the vector store
        """
        if not documents:
            return {"added": 0, "message": "No documents to add"}

        start_time = datetime.now()

        # Generate embeddings
        logger.info(f"Generating embeddings for {len(documents)} chunks...")
        embeddings = self.embedding_service.embed_documents(documents)

        # Add to store
        added = 0
        for doc, embedding in zip(documents, embeddings):
            chunk_id = doc.metadata.get("chunk_id", f"chunk_{len(self.entries)}")

            # Check if already exists
            existing_ids = {e.chunk_id for e in self.entries}
            if chunk_id in existing_ids:
                continue

            entry = VectorEntry(
                chunk_id=chunk_id,
                embedding=embedding,
                text=doc.page_content,
                metadata=doc.metadata,
            )
            self.entries.append(entry)
            added += 1

        # Persist
        self._save()
        self._init_bm25()

        elapsed = (datetime.now() - start_time).total_seconds()

        result = {
            "added": added,
            "collection_size": len(self.entries),
            "time_seconds": elapsed,
        }

        logger.success(f"Added {added} chunks to vector store in {elapsed:.2f}s")
        return result

    def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_dict: Optional[Dict] = None,
        min_score: Optional[float] = None,
        hybrid_weight: float = 0.5,
    ) -> SearchResults:
        """
        Perform hybrid search (Semantic + Keyword)

        Args:
            query: User query string
            top_k: Number of results to return
            filter_dict: Optional metadata filter
            min_score: Minimum combined score threshold
            hybrid_weight: Weight for vector search (0-1).
                          0 = Keyword only, 1 = Vector only.
        """
        start_time = datetime.now()
        top_k = top_k or self.settings.top_k_results
        min_score = (
            min_score if min_score is not None else self.settings.similarity_threshold
        )

        if not self.entries:
            return SearchResults(
                query=query, results=[], search_time_ms=0, total_documents=0
            )

        # Generate query embedding
        query_embedding = self.embedding_service.embed_text(query)

        # Calculate similarities
        results = []
        for entry in self.entries:
            # Apply filter if provided
            if filter_dict:
                match = all(entry.metadata.get(k) == v for k, v in filter_dict.items())
                if not match:
                    continue

            score = cosine_similarity(query_embedding, entry.embedding)

            if score >= min_score:
                results.append(
                    SearchResult(
                        chunk_id=entry.chunk_id,
                        content=entry.text,
                        score=float(score),
                        metadata=entry.metadata,
                    )
                )

        # Apply BM25 ranking if available
        if self.bm25 and hybrid_weight < 1.0:
            tokenized_query = self._tokenize(query)
            bm25_scores = self.bm25.get_scores(tokenized_query)

            # Normalize BM25 scores to 0-1 range
            if len(bm25_scores) > 0:
                max_bm25 = max(bm25_scores)
                if max_bm25 > 0:
                    bm25_scores = [float(s / max_bm25) for s in bm25_scores]
                else:
                    bm25_scores = [0.0] * len(self.entries)

            # Hybrid Calculation
            hybrid_results = []
            for i, entry in enumerate(self.entries):
                # Apply filter
                if filter_dict:
                    match = all(
                        entry.metadata.get(k) == v for k, v in filter_dict.items()
                    )
                    if not match:
                        continue

                # Semantic Score
                v_score = cosine_similarity(query_embedding, entry.embedding)

                # Keyword Score
                k_score = bm25_scores[i] if i < len(bm25_scores) else 0.0

                # Weighted Combination
                combined_score = (v_score * hybrid_weight) + (
                    k_score * (1.0 - hybrid_weight)
                )

                if combined_score >= min_score:
                    hybrid_results.append(
                        SearchResult(
                            chunk_id=entry.chunk_id,
                            content=entry.text,
                            score=float(combined_score),
                            metadata=entry.metadata,
                        )
                    )
            results = hybrid_results

        # Sort by score descending and take top k
        results.sort(key=lambda x: x.score, reverse=True)
        results = results[:top_k]

        elapsed = (datetime.now() - start_time).total_seconds() * 1000

        return SearchResults(
            query=query,
            results=results,
            search_time_ms=elapsed,
            total_documents=len(self.entries),
        )

    def get_document_chunks(self, doc_id: str) -> List[SearchResult]:
        """Get all chunks for a specific document"""
        chunks = []
        for entry in self.entries:
            if entry.metadata.get("doc_id") == doc_id:
                chunks.append(
                    SearchResult(
                        chunk_id=entry.chunk_id,
                        content=entry.text,
                        score=1.0,
                        metadata=entry.metadata,
                    )
                )
        return chunks

    def delete_document(self, doc_id: str) -> Dict[str, Any]:
        """Delete all chunks for a document"""
        original_count = len(self.entries)
        self.entries = [e for e in self.entries if e.metadata.get("doc_id") != doc_id]
        deleted = original_count - len(self.entries)

        if deleted > 0:
            self._save()
            logger.info(f"Deleted {deleted} chunks for document: {doc_id}")

        return {"deleted": deleted, "doc_id": doc_id}

    def list_documents(self) -> List[Dict[str, Any]]:
        """Get list of all unique documents in the store"""
        documents = {}
        for entry in self.entries:
            doc_id = entry.metadata.get("doc_id", "unknown")
            if doc_id not in documents:
                documents[doc_id] = {
                    "doc_id": doc_id,
                    "source": entry.metadata.get("source", "Unknown"),
                    "file_type": entry.metadata.get("file_type", ""),
                    "chunks": 0,
                }
            documents[doc_id]["chunks"] += 1

        return list(documents.values())

    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        documents = self.list_documents()

        return {
            "total_chunks": len(self.entries),
            "total_documents": len(documents),
            "collection_name": "in_memory",
            "documents": documents,
        }

    def clear(self) -> Dict[str, Any]:
        """Clear all documents from the store"""
        count = len(self.entries)
        self.entries = []
        self._save()

        logger.warning(f"Cleared {count} chunks from vector store")
        return {"deleted": count}


# Convenience function
def get_vector_store() -> VectorStore:
    """Get singleton vector store instance"""
    return VectorStore()
