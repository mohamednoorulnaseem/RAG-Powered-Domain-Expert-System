import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure stdout to use UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv()

from core.embeddings import HuggingFaceEmbeddingService
from core.vector_store import VectorStore
from core.query_engine import QueryEngine
from core.agent import SelfCorrectingRAGAgent
from core.db import SessionLocal, Job, Attempt, init_db

def test_db_logging():
    print("=" * 70)
    print("💾 Testing Database Logging with SQLite Fallback")
    print("=" * 70)
    
    # 1. Initialize DB and engine
    init_db()
    
    # 2. Setup agent
    embedding_service = HuggingFaceEmbeddingService()
    vector_store = VectorStore(embedding_service=embedding_service)
    query_engine = QueryEngine(vector_store=vector_store)
    agent = SelfCorrectingRAGAgent(query_engine=query_engine)
    
    # 3. Define a query and run it with a unique test job ID
    test_job_id = "test_job_uuid_999"
    query = "Who is John Michael Smith reporting to?"
    
    # Clean previous test entries if any
    db = SessionLocal()
    try:
        db.query(Job).filter(Job.job_id == test_job_id).delete()
        db.commit()
    except Exception as e:
        db.rollback()
    finally:
        db.close()
        
    print(f"Running agent with job_id: {test_job_id}")
    result = agent.run(query=query, job_id=test_job_id)
    
    # 4. Verify DB entries
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.job_id == test_job_id).first()
        attempts = db.query(Attempt).filter(Attempt.job_id == test_job_id).all()
        
        print("\n" + "=" * 70)
        print("📊 DATABASE RECORDS FOUND:")
        print("=" * 70)
        if job:
            print(f"Job ID: {job.job_id}")
            print(f"  Status       : {job.status}")
            print(f"  Original Query: {job.original_query}")
            print(f"  Final Answer : {job.final_answer[:150]}...")
            print(f"  Created At   : {job.created_at}")
            print(f"  Completed At : {job.completed_at}")
        else:
            print("ERROR: Job entry not found in database!")
            sys.exit(1)
            
        print("-" * 50)
        print(f"Attempts Logged: {len(attempts)}")
        for i, att in enumerate(attempts):
            print(f"  Attempt #{att.attempt_number}:")
            print(f"    Query used  : {att.query_text}")
            print(f"    Faithfulness: {att.faithfulness_score}")
            print(f"    Relevancy   : {att.relevance_score}")
            print(f"    Created At  : {att.created_at}")
        
        if len(attempts) > 0:
            print("\n✅ Verification successful! DB Logging works.")
        else:
            print("\n❌ Verification failed. No attempts logged in DB.")
            sys.exit(1)
            
    except Exception as e:
        print(f"Database query failed: {e}")
        sys.exit(1)
    finally:
        db.close()
    print("=" * 70)

if __name__ == "__main__":
    test_db_logging()
