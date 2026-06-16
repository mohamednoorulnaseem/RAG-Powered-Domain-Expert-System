import os
import sys
from pathlib import Path
from celery import Celery
from loguru import logger

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_settings
from core.embeddings import HuggingFaceEmbeddingService
from core.vector_store import VectorStore
from core.query_engine import QueryEngine
from core.agent import SelfCorrectingRAGAgent
from core.db import SessionLocal, Job

settings = get_settings()
redis_url = settings.redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "rag_tasks",
    broker=redis_url,
    backend=redis_url
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

@celery_app.task(name="core.celery_worker.run_agent_task")
def run_agent_task(job_id: str, query: str):
    logger.info(f"Starting async Celery task for job: {job_id} with query: {query}")
    
    # Update DB job status to RUNNING
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.job_id == job_id).first()
        if job:
            job.status = "RUNNING"
            db.commit()
    except Exception as e:
        logger.error(f"Failed to update Job status to RUNNING in celery task: {e}")
    finally:
        db.close()
        
    try:
        # Initialize components on the worker
        embedding_service = HuggingFaceEmbeddingService()
        vector_store = VectorStore(embedding_service=embedding_service)
        query_engine = QueryEngine(vector_store=vector_store)
        agent = SelfCorrectingRAGAgent(query_engine=query_engine)
        
        # Run agent (this automatically handles DB logging inside SelfCorrectingRAGAgent.run)
        result = agent.run(query=query, job_id=job_id)
        
        logger.success(f"Celery task succeeded for job: {job_id}")
        return {
            "success": True,
            "job_id": job_id,
            "final_answer": result["generation"],
            "attempts": result["attempts"],
            "faithfulness": result["faithfulness_score"],
            "relevancy": result["answer_relevance_score"]
        }
    except Exception as e:
        logger.error(f"Celery task failed for job: {job_id}: {e}")
        # Update job status in case agent.run crashed early
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.job_id == job_id).first()
            if job:
                job.status = "FAILED"
                db.commit()
        except Exception as db_err:
            logger.error(f"Failed to mark Job as FAILED in DB: {db_err}")
        finally:
            db.close()
        return {
            "success": False,
            "job_id": job_id,
            "error": str(e)
        }
