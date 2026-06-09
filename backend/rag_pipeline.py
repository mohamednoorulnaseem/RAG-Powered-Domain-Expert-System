"""
rag_pipeline.py — Core RAG Pipeline

Orchestrates the full Retrieval-Augmented Generation flow:
1. Document ingestion: load → chunk → embed → store in FAISS
2. Query: embed question → FAISS similarity search → build context → GPT-4o → answer + sources

The FAISS index lives in memory for fast retrieval. Documents can be added
and removed dynamically without restarting the server.
"""

import os
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from document_processor import DocumentProcessor
from embeddings import EmbeddingsManager

logger = logging.getLogger(__name__)


# The system prompt that enforces grounded, citation-based answers
SYSTEM_PROMPT = """You are a precise document analysis assistant. Your role is to answer questions based ONLY on the provided context from uploaded documents.

Rules:
1. Answer ONLY from the provided context. Do not use any external knowledge.
2. If the answer is not in the context, respond with: "I could not find this information in the uploaded documents."
3. Be concise and accurate. Provide direct answers without unnecessary preamble.
4. When possible, reference which document and section your answer comes from.
5. If the context contains partial information, state what you found and note that the information may be incomplete.
6. Format your response with markdown for readability (bullet points, bold, etc.) when appropriate."""


class RAGPipeline:
    """
    Central RAG pipeline managing document ingestion, vector storage, and query answering.

    Architecture:
    - Uses FAISS for in-memory vector similarity search (fast, no external DB needed)
    - Documents are tracked by doc_id so they can be individually removed
    - The FAISS index is rebuilt when documents are removed (FAISS doesn't support deletion natively)
    """

    def __init__(self):
        self.processor = DocumentProcessor()
        # Store all document chunks in memory, keyed by doc_id
        # This allows us to rebuild the FAISS index when documents are removed
        self.document_chunks: Dict[str, List[Document]] = {}
        # The FAISS vector store — None until the first document is added
        self.vector_store: Optional[FAISS] = None
        # Track document metadata for the /documents endpoint
        self.document_metadata: Dict[str, Dict[str, Any]] = {}

    @property
    def has_documents(self) -> bool:
        """Check if any documents have been indexed."""
        return len(self.document_chunks) > 0

    def add_document(
        self,
        file_path: str,
        doc_id: str,
        original_filename: str,
        api_key: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> Dict[str, Any]:
        """
        Process a document and add it to the FAISS index.

        Flow: load file → split into chunks → generate embeddings → add to FAISS

        Args:
            file_path: Path to the uploaded file on disk.
            doc_id: Unique identifier for this document.
            original_filename: Original filename for display/citation.
            api_key: OpenAI API key for generating embeddings.
            chunk_size: Characters per chunk.
            chunk_overlap: Overlap between chunks.

        Returns:
            Dict with document metadata (id, name, chunk count, status).
        """
        # Step 1: Load and chunk the document
        chunks = self.processor.load_and_split(
            file_path=file_path,
            doc_id=doc_id,
            original_filename=original_filename,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        logger.info(f"Document '{original_filename}' split into {len(chunks)} chunks")

        # Step 2: Get embeddings model
        embeddings = EmbeddingsManager.get_embeddings(api_key)

        # Step 3: Add to FAISS index
        if self.vector_store is None:
            # First document — create the FAISS index from scratch
            self.vector_store = FAISS.from_documents(chunks, embeddings)
        else:
            # Subsequent documents — add to existing index
            self.vector_store.add_documents(chunks)

        # Step 4: Store chunks and metadata for later reference
        self.document_chunks[doc_id] = chunks
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        self.document_metadata[doc_id] = {
            "id": doc_id,
            "filename": original_filename,
            "chunk_count": len(chunks),
            "file_size": file_size,
            "status": "ready",
        }

        return self.document_metadata[doc_id]

    def remove_document(self, doc_id: str, api_key: str) -> bool:
        """
        Remove a document from the index.

        Since FAISS doesn't support native deletion, we rebuild the entire index
        from the remaining documents. This is acceptable because:
        - Document count is typically small (tens, not millions)
        - Rebuilding is fast for small indices
        - It guarantees a clean index state

        Args:
            doc_id: ID of the document to remove.
            api_key: OpenAI API key (needed to rebuild embeddings).

        Returns:
            True if the document was found and removed.
        """
        if doc_id not in self.document_chunks:
            return False

        # Remove from our tracking structures
        del self.document_chunks[doc_id]
        del self.document_metadata[doc_id]

        # Rebuild the FAISS index from remaining documents
        if self.document_chunks:
            all_chunks = []
            for chunks in self.document_chunks.values():
                all_chunks.extend(chunks)

            embeddings = EmbeddingsManager.get_embeddings(api_key)
            self.vector_store = FAISS.from_documents(all_chunks, embeddings)
        else:
            # No documents left — clear the index
            self.vector_store = None

        logger.info(f"Document {doc_id} removed. Index rebuilt with {len(self.document_chunks)} remaining documents.")
        return True

    def query(
        self,
        question: str,
        api_key: str,
        model: str = "gpt-4o",
        top_k: int = 5,
        temperature: float = 0.1,
    ) -> Dict[str, Any]:
        """
        Answer a question using the RAG pipeline.

        Flow: embed question → FAISS similarity search → build context → GPT-4o → answer

        Args:
            question: The user's natural language question.
            api_key: OpenAI API key.
            model: Chat model to use (gpt-4o, gpt-4o-mini).
            top_k: Number of most similar chunks to retrieve.
            temperature: LLM temperature (0 = deterministic, 1 = creative).

        Returns:
            Dict with 'answer' (str) and 'sources' (list of citation dicts).
        """
        if not self.has_documents or self.vector_store is None:
            return {
                "answer": "No documents have been uploaded yet. Please upload a document first.",
                "sources": [],
            }

        # Step 1: Retrieve the top-k most similar chunks
        retrieved_docs = self.vector_store.similarity_search(question, k=top_k)

        if not retrieved_docs:
            return {
                "answer": "I could not find relevant information in the uploaded documents.",
                "sources": [],
            }

        # Step 2: Build context string from retrieved chunks
        context_parts = []
        sources = []
        seen_sources = set()

        for i, doc in enumerate(retrieved_docs):
            context_parts.append(
                f"[Source {i + 1} — {doc.metadata.get('source', 'Unknown')}, "
                f"Page {doc.metadata.get('page', 'N/A')}]\n{doc.page_content}"
            )

            # Build unique source citations
            source_key = f"{doc.metadata.get('source', '')}_{doc.metadata.get('page', 0)}"
            if source_key not in seen_sources:
                seen_sources.add(source_key)
                sources.append({
                    "document": doc.metadata.get("source", "Unknown"),
                    "page": doc.metadata.get("page", 0),
                    "chunk_index": doc.metadata.get("chunk_index", 0),
                    "content_preview": doc.page_content[:150] + "..." if len(doc.page_content) > 150 else doc.page_content,
                })

        context = "\n\n---\n\n".join(context_parts)

        # Step 3: Call the LLM with context
        llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            openai_api_key=api_key,
        )

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"Context from uploaded documents:\n\n{context}\n\n---\n\nQuestion: {question}"),
        ]

        response = llm.invoke(messages)

        return {
            "answer": response.content,
            "sources": sources,
        }

    async def query_stream(
        self,
        question: str,
        api_key: str,
        model: str = "gpt-4o",
        top_k: int = 5,
        temperature: float = 0.1,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream an answer token-by-token using the RAG pipeline.

        Same as query() but yields tokens as they arrive from the LLM.
        The final yield includes source citations.

        Yields:
            Dicts with either:
              - {"type": "token", "content": "..."} for each token
              - {"type": "sources", "sources": [...]} at the end
              - {"type": "error", "content": "..."} on error
        """
        if not self.has_documents or self.vector_store is None:
            yield {
                "type": "token",
                "content": "No documents have been uploaded yet. Please upload a document first.",
            }
            yield {"type": "done", "sources": []}
            return

        # Step 1: Retrieve relevant chunks
        try:
            retrieved_docs = self.vector_store.similarity_search(question, k=top_k)
        except Exception as e:
            logger.error(f"FAISS search failed: {e}")
            yield {"type": "error", "content": f"Search failed: {str(e)}"}
            return

        if not retrieved_docs:
            yield {
                "type": "token",
                "content": "I could not find relevant information in the uploaded documents.",
            }
            yield {"type": "done", "sources": []}
            return

        # Step 2: Build context and source citations
        context_parts = []
        sources = []
        seen_sources = set()

        for i, doc in enumerate(retrieved_docs):
            context_parts.append(
                f"[Source {i + 1} — {doc.metadata.get('source', 'Unknown')}, "
                f"Page {doc.metadata.get('page', 'N/A')}]\n{doc.page_content}"
            )

            source_key = f"{doc.metadata.get('source', '')}_{doc.metadata.get('page', 0)}"
            if source_key not in seen_sources:
                seen_sources.add(source_key)
                sources.append({
                    "document": doc.metadata.get("source", "Unknown"),
                    "page": doc.metadata.get("page", 0),
                    "chunk_index": doc.metadata.get("chunk_index", 0),
                    "content_preview": doc.page_content[:150] + "..." if len(doc.page_content) > 150 else doc.page_content,
                })

        context = "\n\n---\n\n".join(context_parts)

        # Step 3: Stream from the LLM
        llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            openai_api_key=api_key,
            streaming=True,
        )

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"Context from uploaded documents:\n\n{context}\n\n---\n\nQuestion: {question}"),
        ]

        try:
            async for chunk in llm.astream(messages):
                if chunk.content:
                    yield {"type": "token", "content": chunk.content}

            # Send sources at the end
            yield {"type": "done", "sources": sources}

        except Exception as e:
            logger.error(f"LLM streaming failed: {e}")
            yield {"type": "error", "content": f"Generation failed: {str(e)}"}

    def get_documents(self) -> List[Dict[str, Any]]:
        """Return metadata for all indexed documents."""
        return list(self.document_metadata.values())

    def clear(self):
        """Reset the entire pipeline — clear FAISS index and all document data."""
        self.vector_store = None
        self.document_chunks.clear()
        self.document_metadata.clear()
        logger.info("RAG pipeline cleared — all documents and index removed.")
