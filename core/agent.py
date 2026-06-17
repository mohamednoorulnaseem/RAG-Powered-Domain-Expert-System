import os
import time
from datetime import datetime
from typing import List, Dict, Any, TypedDict, Optional
from loguru import logger

from langgraph.graph import StateGraph, END
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import Faithfulness, AnswerRelevancy
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.run_config import RunConfig
from langchain_groq import ChatGroq
from langchain_community.embeddings import HuggingFaceEmbeddings
from openai import OpenAI

from core.vector_store import VectorStore, SearchResult
from core.query_engine import QueryEngine
from config import get_settings


# Define state schema
class AgentState(TypedDict):
    query: str
    original_query: str
    retrieved_docs: List[Dict[str, Any]]
    reranked_docs: List[Dict[str, Any]]
    generation: str
    faithfulness_score: float
    answer_relevance_score: float
    attempts: int
    history: List[Dict[str, Any]]
    job_id: Optional[str]


class RagasEvaluator:
    """Handles on-the-fly evaluation using Ragas"""

    def __init__(self, groq_key: str):
        self.groq_key = groq_key
        self.groq_llm = ChatGroq(
            model="llama-3.1-8b-instant", groq_api_key=groq_key, temperature=0.0
        )
        self.ragas_llm = LangchainLLMWrapper(self.groq_llm)
        self.local_emb = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        self.ragas_embeddings = LangchainEmbeddingsWrapper(self.local_emb)
        self.faithfulness_metric = Faithfulness()
        self.relevancy_metric = AnswerRelevancy(strictness=1)
        self.run_config = RunConfig(max_workers=1)

    def evaluate_sample(
        self, question: str, answer: str, contexts: List[str]
    ) -> Dict[str, float]:
        dataset = Dataset.from_dict(
            {"question": [question], "answer": [answer], "contexts": [contexts]}
        )
        try:
            res = evaluate(
                dataset=dataset,
                metrics=[self.faithfulness_metric, self.relevancy_metric],
                llm=self.ragas_llm,
                embeddings=self.ragas_embeddings,
                run_config=self.run_config,
            )
            scores = getattr(res, "_repr_dict", {})
            return {
                "faithfulness": float(scores.get("faithfulness", 0.0)),
                "answer_relevancy": float(scores.get("answer_relevancy", 0.0)),
            }
        except Exception as e:
            logger.error(f"On-the-fly Ragas evaluation failed: {e}")
            return {"faithfulness": 0.0, "answer_relevancy": 0.0}


class SelfCorrectingRAGAgent:
    """Self-Correcting RAG Agent using LangGraph"""

    def __init__(self, query_engine: QueryEngine):
        self.query_engine = query_engine
        self.settings = get_settings()
        self.groq_key = os.getenv("GROQ_API_KEY", "")
        self.evaluator = RagasEvaluator(self.groq_key)
        self.client = OpenAI(
            api_key=self.groq_key, base_url="https://api.groq.com/openai/v1"
        )

        # Compile graph
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("retrieve", self.node_retrieve)
        workflow.add_node("rerank", self.node_rerank)
        workflow.add_node("generate", self.node_generate)
        workflow.add_node("evaluate", self.node_evaluate)
        workflow.add_node("rewrite_query", self.node_rewrite_query)

        # Set entry point
        workflow.set_entry_point("retrieve")

        # Add edges
        workflow.add_edge("retrieve", "rerank")
        workflow.add_edge("rerank", "generate")
        workflow.add_edge("generate", "evaluate")

        # Conditional edge routing after evaluation
        workflow.add_conditional_edges(
            "evaluate",
            self.route_after_evaluation,
            {"continue": "rewrite_query", "end": END},
        )

        # Loop edge from rewrite back to retrieve
        workflow.add_edge("rewrite_query", "retrieve")

        return workflow.compile()

    # --- Node Implementations ---

    def node_retrieve(self, state: AgentState) -> Dict[str, Any]:
        """Node 1: Retrieve candidate passages from vector store"""
        # Search vector store for top 20 candidates, bypass min_score filtering for recall stage
        logger.info(
            f"Vector store has {len(self.query_engine.vector_store.entries)} entries."
        )
        search_results = self.query_engine.vector_store.search(
            query=state["query"], top_k=20, min_score=0.0
        )

        retrieved = [
            {
                "content": r.content,
                "score": r.score,
                "metadata": r.metadata,
                "source": r.source,
                "page": r.page,
            }
            for r in search_results.results
        ]

        return {"retrieved_docs": retrieved, "attempts": state.get("attempts", 0) + 1}

    def node_rerank(self, state: AgentState) -> Dict[str, Any]:
        """Node 2: Run Cross-Encoder reranking to choose top 5 passages"""
        logger.info(
            f"--- Node [rerank]: Reranking {len(state['retrieved_docs'])} candidates ---"
        )

        retrieved = state["retrieved_docs"]
        if not retrieved:
            return {"reranked_docs": []}

        import math

        pairs = [[state["query"], doc["content"]] for doc in retrieved]
        rerank_scores = self.query_engine.reranker.predict(pairs)

        # Convert and apply sigmoid
        for doc, score in zip(retrieved, rerank_scores):
            doc["score"] = 1 / (1 + math.exp(-float(score)))

        # Re-sort descending and slice to top-5
        retrieved.sort(key=lambda x: x["score"], reverse=True)
        reranked = retrieved[:5]

        return {"reranked_docs": reranked}

    def node_generate(self, state: AgentState) -> Dict[str, Any]:
        """Node 3: Generate the RAG response"""
        logger.info(f"--- Node [generate]: Producing LLM answer ---")

        # Build context
        context_parts = []
        for doc in state["reranked_docs"]:
            source = doc.get("source", "Unknown")
            page = doc.get("page", "?")
            context_parts.append(f"[Source: {source}, Page {page}]\n{doc['content']}")
        context = "\n\n---\n\n".join(context_parts)

        # Invoke generation
        gen_result = self.query_engine._generate_answer(
            query=state["query"], context=context
        )

        return {"generation": gen_result["answer"]}

    def node_evaluate(self, state: AgentState) -> Dict[str, Any]:
        """Node 4: Evaluate faithfulness & answer relevancy on-the-fly"""
        logger.info(f"--- Node [evaluate]: Scoring generated answer ---")

        contexts = [doc["content"] for doc in state["reranked_docs"]]
        scores = self.evaluator.evaluate_sample(
            question=state["query"], answer=state["generation"], contexts=contexts
        )

        faithfulness = scores.get("faithfulness", 0.0)
        relevancy = scores.get("answer_relevancy", 0.0)

        logger.info(
            f"Scores -> Faithfulness: {faithfulness:.4f}, Relevancy: {relevancy:.4f} (Attempt {state['attempts']})"
        )

        # Log attempt to database
        job_id = state.get("job_id")
        if job_id:
            from core.db import SessionLocal, Attempt

            db = SessionLocal()
            try:
                attempt = Attempt(
                    job_id=job_id,
                    attempt_number=state["attempts"],
                    query_text=state["query"],
                    faithfulness_score=faithfulness,
                    relevance_score=relevancy,
                    generated_answer=state["generation"],
                )
                db.add(attempt)
                db.commit()
                logger.info(f"Logged attempt {state['attempts']} to database.")
            except Exception as e:
                logger.error(f"Failed to log attempt to database: {e}")
            finally:
                db.close()

        return {"faithfulness_score": faithfulness, "answer_relevance_score": relevancy}

    def node_rewrite_query(self, state: AgentState) -> Dict[str, Any]:
        """Node 5: Rewrite query based on feedback from the failed attempt"""
        logger.info(f"--- Node [rewrite_query]: Rewriting query... ---")

        history_item = {
            "attempt": state["attempts"],
            "query": state["query"],
            "generation": state["generation"],
            "faithfulness": state["faithfulness_score"],
            "relevancy": state["answer_relevance_score"],
        }

        new_history = state.get("history", []) + [history_item]

        # Call LLM to rewrite query
        prompt = f"""You are a query re-writer helper for a search system.
The user's original query is: "{state['original_query']}"
The current search query was: "{state['query']}"
The RAG system generated this answer: "{state['generation']}"

This answer failed our verification checks because it wasn't faithful to the retrieved context or didn't answer the question relevantly.
Please rewrite the search query to retrieve better and more specific matching passages from the vector database.
Only return the rewritten query text. Do not add quotes, explanation, or introductions.

Rewritten search query:"""

        response = self.client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise search query optimizer.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        )

        rewritten = response.choices[0].message.content.strip().strip('"')
        logger.info(f"Rewritten Query: {rewritten}")

        return {"query": rewritten, "history": new_history}

    # --- Router ---

    def route_after_evaluation(self, state: AgentState) -> str:
        """Determines if the pipeline should END or retry rewriting the query"""
        # Threshold: Faithfulness >= 0.8 and Relevancy >= 0.8
        is_satisfactory = (state["faithfulness_score"] >= 0.80) and (
            state["answer_relevance_score"] >= 0.80
        )
        max_attempts_reached = state["attempts"] >= 3

        if is_satisfactory or max_attempts_reached:
            if max_attempts_reached and not is_satisfactory:
                logger.warning(
                    "Max generation attempts (3) reached. Exiting agent loop with best effort response."
                )
            else:
                logger.success("Agent evaluation criteria met successfully.")
            return "end"

        logger.info(
            "Evaluation criteria not met. Routing to query rewriting node for another attempt."
        )
        return "continue"

    # --- Run Pipeline ---

    def run(self, query: str, job_id: Optional[str] = None) -> Dict[str, Any]:
        # Initialize DB job if job_id is provided
        if job_id:
            from core.db import SessionLocal, Job, init_db

            init_db()  # Ensure tables exist
            db = SessionLocal()
            try:
                job = db.query(Job).filter(Job.job_id == job_id).first()
                if not job:
                    job = Job(job_id=job_id, status="RUNNING", original_query=query)
                    db.add(job)
                else:
                    job.status = "RUNNING"
                db.commit()
            except Exception as e:
                logger.error(f"Failed to initialize Job in DB: {e}")
            finally:
                db.close()

        initial_state = {
            "query": query,
            "original_query": query,
            "retrieved_docs": [],
            "reranked_docs": [],
            "generation": "",
            "faithfulness_score": 0.0,
            "answer_relevance_score": 0.0,
            "attempts": 0,
            "history": [],
            "job_id": job_id,
        }

        try:
            final_state = self.graph.invoke(initial_state)

            # Update DB job on success
            if job_id:
                from core.db import SessionLocal, Job

                db = SessionLocal()
                try:
                    job = db.query(Job).filter(Job.job_id == job_id).first()
                    if job:
                        job.status = "COMPLETED"
                        job.final_answer = final_state["generation"]
                        job.completed_at = datetime.utcnow()
                        db.commit()
                except Exception as e:
                    logger.error(f"Failed to update Job success in DB: {e}")
                finally:
                    db.close()

            return final_state
        except Exception as e:
            # Update DB job on failure
            if job_id:
                from core.db import SessionLocal, Job

                db = SessionLocal()
                try:
                    job = db.query(Job).filter(Job.job_id == job_id).first()
                    if job:
                        job.status = "FAILED"
                        job.completed_at = datetime.utcnow()
                        db.commit()
                except Exception as e:
                    logger.error(f"Failed to update Job failure in DB: {e}")
                finally:
                    db.close()
            raise e
