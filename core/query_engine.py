"""
RAG Expert System - Query Engine
Handles RAG pipeline: retrieval + generation
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from openai import OpenAI
from loguru import logger

from config import (
    get_settings,
    SYSTEM_PROMPT,
    QUERY_PROMPT_TEMPLATE,
    SUMMARY_PROMPT_TEMPLATE,
)
from core.vector_store import VectorStore, SearchResult, SearchResults


@dataclass
class Citation:
    """Represents a source citation"""

    source: str
    page: int
    chunk: int
    score: float
    excerpt: str  # Relevant excerpt from the chunk


@dataclass
class QueryResponse:
    """Complete response to a user query"""

    query: str
    answer: str
    citations: List[Citation]
    confidence: str  # High, Medium, Low
    search_time_ms: float
    generation_time_ms: float
    total_time_ms: float
    chunks_retrieved: int
    model_used: str
    usage: Dict[str, int]  # prompt_tokens, completion_tokens, total_tokens

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "answer": self.answer,
            "citations": [
                {
                    "source": c.source,
                    "page": c.page,
                    "chunk": c.chunk,
                    "score": round(c.score, 3),
                    "excerpt": (
                        c.excerpt[:200] + "..." if len(c.excerpt) > 200 else c.excerpt
                    ),
                }
                for c in self.citations
            ],
            "confidence": self.confidence,
            "metrics": {
                "search_time_ms": round(self.search_time_ms, 2),
                "generation_time_ms": round(self.generation_time_ms, 2),
                "total_time_ms": round(self.total_time_ms, 2),
                "chunks_retrieved": self.chunks_retrieved,
                "model": self.model_used,
                "usage": self.usage,
                "estimated_cost_usd": self._calculate_cost(),
            },
        }

    def _calculate_cost(self) -> float:
        """Estimate cost based on current OpenAI pricing for GPT-4 Turbo"""
        # GPT-4 Turbo pricing: $10.00 / 1M input tokens, $30.00 / 1M output tokens
        prompt_cost = (self.usage.get("prompt_tokens", 0) / 1_000_000) * 10.0
        completion_cost = (self.usage.get("completion_tokens", 0) / 1_000_000) * 30.0
        return prompt_cost + completion_cost


class QueryEngine:
    """
    RAG Query Engine

    Complete RAG Pipeline:
    1. Receive user question
    2. Search vector store for relevant chunks
    3. Build context from retrieved chunks
    4. Generate answer using LLM
    5. Return answer with citations
    """

    def __init__(self, vector_store: Optional[VectorStore] = None):
        self.settings = get_settings()
        self.vector_store = vector_store or VectorStore()
        # Auto-routing fallback to Groq if OpenAI key is default or missing
        import os

        api_key = self.settings.openai_api_key
        base_url = os.getenv("OPENAI_BASE_URL", None)

        groq_key = os.getenv("GROQ_API_KEY", "")
        if groq_key and (
            not api_key or "your-api-key" in api_key or "sk-your-api-key" in api_key
        ):
            logger.info(
                "No valid OpenAI API key detected. Falling back to Groq provider for LLM completions."
            )
            api_key = groq_key
            base_url = "https://api.groq.com/openai/v1"
            # Update settings object llm_model dynamically to Llama model
            self.settings.llm_model = "llama-3.1-8b-instant"
            os.environ["LLM_MODEL"] = "llama-3.1-8b-instant"

        self._api_key = api_key
        self._base_url = base_url
        self._client = None

        # In-memory history: session_id -> list of message dicts
        self.history: Dict[str, List[Dict[str, str]]] = {}
        self.max_history = 10  # Store last 10 messages

        # Initialize CrossEncoder for re-ranking
        logger.info(
            "Initializing CrossEncoder re-ranker model: cross-encoder/ms-marco-MiniLM-L-6-v2..."
        )
        from sentence_transformers import CrossEncoder
        import torch

        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"CrossEncoder using device: {device}")
        self.reranker = CrossEncoder(
            "cross-encoder/ms-marco-MiniLM-L-6-v2", device=device
        )

        logger.info(f"QueryEngine initialized with model: {self.settings.llm_model}")

    @property
    def client(self):
        if self._client is None:
            api_key = self._api_key
            if not api_key or "your-api-key" in api_key:
                api_key = "mock_key_for_testing"
            self._client = OpenAI(api_key=api_key, base_url=self._base_url)
        return self._client

    def _get_history(self, session_id: str) -> List[Dict[str, str]]:
        """Get message history for a session"""
        return self.history.get(session_id, [])

    def _update_history(self, session_id: str, role: str, content: str):
        """Update message history for a session"""
        if session_id not in self.history:
            self.history[session_id] = []

        self.history[session_id].append({"role": role, "content": content})

        # Keep only the last N messages
        if len(self.history[session_id]) > self.max_history:
            self.history[session_id] = self.history[session_id][-self.max_history :]

    def _build_context(self, search_results: SearchResults) -> str:
        """
        Build context string from retrieved chunks

        Format:
        [Source: document.pdf, Page 1]
        Content of chunk 1...

        [Source: document.pdf, Page 2]
        Content of chunk 2...
        """
        context_parts = []

        for result in search_results.results:
            source = result.metadata.get("source", "Unknown")
            page = result.metadata.get("page", "?")

            context_parts.append(f"[Source: {source}, Page {page}]\n{result.content}")

        return "\n\n---\n\n".join(context_parts)

    def _calculate_confidence(self, search_results: SearchResults) -> str:
        """
        Calculate confidence level based on search results

        High: Best score >= 0.85 and multiple relevant chunks
        Medium: Best score >= 0.70
        Low: Best score < 0.70 or few results
        """
        if not search_results.has_results:
            return "Low"

        best_score = search_results.best_score
        num_good_results = sum(1 for r in search_results.results if r.score >= 0.7)

        if best_score >= 0.85 and num_good_results >= 2:
            return "High"
        elif best_score >= 0.70:
            return "Medium"
        else:
            return "Low"

    def _generate_answer(
        self, query: str, context: str, session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate answer using LLM and return both content and usage info"""

        prompt = QUERY_PROMPT_TEMPLATE.format(context=context, question=query)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Add history if session_id is provided
        if session_id:
            messages.extend(self._get_history(session_id))

        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.settings.llm_model,
            messages=messages,
            temperature=self.settings.temperature,
            max_tokens=self.settings.max_tokens,
        )

        answer = response.choices[0].message.content
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }

        # Save to history if session_id is provided
        if session_id:
            self._update_history(session_id, "user", query)
            self._update_history(session_id, "assistant", answer)

        return {"answer": answer, "usage": usage}

    def query(
        self,
        question: str,
        top_k: Optional[int] = None,
        min_score: Optional[float] = None,
        session_id: Optional[str] = None,
        hybrid_weight: float = 0.5,
    ) -> QueryResponse:
        """
        Execute complete RAG query pipeline

        Args:
            question: User's question
            top_k: Number of chunks to retrieve
            min_score: Minimum similarity score threshold

        Returns:
            QueryResponse with answer, citations, and metrics
        """
        start_time = datetime.now()

        # Step 1: Search for relevant candidate chunks (retrieve top 20 or top_k * 4 if top_k is large)
        requested_k = top_k or 5
        candidate_k = max(20, requested_k * 4)
        logger.info(
            f"Retrieving top {candidate_k} candidates from vector store for query: {question[:50]}..."
        )
        search_results = self.vector_store.search(
            query=question,
            top_k=candidate_k,
            min_score=min_score or 0.0,
            hybrid_weight=hybrid_weight,
        )
        search_time = search_results.search_time_ms

        # Step 1.5: Cross-Encoder Re-ranking
        if search_results.has_results:
            logger.info(
                f"Reranking {len(search_results.results)} candidates with Cross-Encoder..."
            )
            import math

            pairs = [[question, r.content] for r in search_results.results]
            rerank_scores = self.reranker.predict(pairs)

            # Update scores with sigmoid of logit
            for r, score in zip(search_results.results, rerank_scores):
                r.score = 1 / (1 + math.exp(-float(score)))

            # Re-sort results by score descending
            search_results.results.sort(key=lambda x: x.score, reverse=True)

            # Select final requested_k results
            search_results.results = search_results.results[:requested_k]

        # Step 2: Check if we have relevant results
        if not search_results.has_results:
            return QueryResponse(
                query=question,
                answer="I cannot find relevant information in the uploaded documents to answer this question. Please try rephrasing your question or ensure the relevant documents have been uploaded.",
                citations=[],
                confidence="Low",
                search_time_ms=search_time,
                generation_time_ms=0,
                total_time_ms=search_time,
                chunks_retrieved=0,
                model_used=self.settings.llm_model,
                usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            )

        # Step 3: Build context from retrieved chunks
        context = self._build_context(search_results)

        # Step 4: Generate answer using LLM
        gen_start = datetime.now()
        gen_result = self._generate_answer(question, context, session_id=session_id)
        answer = gen_result["answer"]
        usage = gen_result["usage"]
        gen_time = (datetime.now() - gen_start).total_seconds() * 1000

        # Step 5: Build citations
        citations = [
            Citation(
                source=r.source,
                page=r.page,
                chunk=r.metadata.get("chunk", 0),
                score=r.score,
                excerpt=r.content,
            )
            for r in search_results.results
        ]

        total_time = (datetime.now() - start_time).total_seconds() * 1000

        response = QueryResponse(
            query=question,
            answer=answer,
            citations=citations,
            confidence=self._calculate_confidence(search_results),
            search_time_ms=search_time,
            generation_time_ms=gen_time,
            total_time_ms=total_time,
            chunks_retrieved=len(search_results.results),
            model_used=self.settings.llm_model,
            usage=usage,
        )

        logger.success(
            f"Query completed in {total_time:.0f}ms with {len(citations)} citations"
        )
        return response

    def summarize_document(self, doc_id: str) -> Dict[str, Any]:
        """Generate a summary of a specific document"""

        # Get all chunks for the document
        chunks = self.vector_store.get_document_chunks(doc_id)

        if not chunks:
            return {"error": f"Document not found: {doc_id}", "summary": None}

        # Combine chunks (limit to first 10 for summary)
        content = "\n\n".join([c.content for c in chunks[:10]])

        prompt = SUMMARY_PROMPT_TEMPLATE.format(content=content)

        response = self.client.chat.completions.create(
            model=self.settings.llm_model,
            messages=[
                {"role": "system", "content": "You are an expert document analyst."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1000,
        )

        return {
            "doc_id": doc_id,
            "source": chunks[0].metadata.get("source", "Unknown"),
            "num_chunks": len(chunks),
            "summary": response.choices[0].message.content,
        }

    def get_similar_chunks(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Get similar chunks without generating an answer (for debugging)"""
        search_results = self.vector_store.search(query=query, top_k=top_k)

        return [
            {
                "chunk_id": r.chunk_id,
                "source": r.source,
                "page": r.page,
                "score": round(r.score, 4),
                "content": r.content,
            }
            for r in search_results.results
        ]


# Convenience function
def get_query_engine() -> QueryEngine:
    """Get query engine instance"""
    return QueryEngine()
