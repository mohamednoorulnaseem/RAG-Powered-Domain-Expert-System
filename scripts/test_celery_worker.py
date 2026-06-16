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

# Set Celery to execute tasks synchronously for testing without Redis broker
from core.celery_worker import celery_app
celery_app.conf.task_always_eager = True
celery_app.conf.task_eager_propagates = True

from fastapi.testclient import TestClient
from api.main import app
from core.db import SessionLocal, Job, Attempt, init_db

def test_celery_flow():
    print("=" * 70)
    print("⚡ Testing Celery Async Queue + FastAPI Integration (Eager Mode)")
    print("=" * 70)
    
    # 1. Initialize database and FastAPI test client
    init_db()
    client = TestClient(app)
    
    # 2. Define test query
    query = "Who is John Michael Smith reporting to?"
    print(f"Submitting asynchronous query: '{query}'")
    
    # 3. Post to /query
    response = client.post("/query", json={"question": query})
    if response.status_code != 200:
        print(f"ERROR: POST /query failed with {response.status_code}: {response.text}")
        sys.exit(1)
        
    data = response.json()
    job_id = data.get("job_id")
    status = data.get("status")
    print(f"Response -> Job ID: {job_id}, Status: {status}")
    
    if not job_id:
        print("ERROR: Job ID not returned in response!")
        sys.exit(1)
        
    # 4. Query /result/{job_id} to verify completion
    print(f"\nPolling result endpoint /result/{job_id}...")
    res_response = client.get(f"/result/{job_id}")
    if res_response.status_code != 200:
        print(f"ERROR: GET /result/{job_id} failed: {res_response.text}")
        sys.exit(1)
        
    res_data = res_response.json()
    print("\n" + "=" * 70)
    print("📋 DOCKER ASYNC FLOW RESULT:")
    print("=" * 70)
    print(f"Job ID       : {res_data['job_id']}")
    print(f"Status       : {res_data['status']}")
    print(f"Query        : {res_data['original_query']}")
    print(f"Answer       : {res_data['answer'][:150]}...")
    print(f"Confidence   : {res_data['confidence']}")
    print(f"Created At   : {res_data['created_at']}")
    print(f"Completed At : {res_data['completed_at']}")
    print("-" * 50)
    print(f"Attempts Logged: {len(res_data['attempts'])}")
    for a in res_data['attempts']:
        print(f"  Attempt #{a['attempt_number']}:")
        print(f"    Query      : {a['query_text']}")
        print(f"    Faithfulness: {a['faithfulness_score']}")
        print(f"    Relevancy  : {a['relevance_score']}")
        
    if res_data['status'] == "COMPLETED" and len(res_data['attempts']) > 0:
        print("\n✅ Verification successful! Celery task & FastAPI poll endpoint integrated.")
    else:
        print("\n❌ Verification failed. Job not completed or attempts missing.")
        sys.exit(1)
    print("=" * 70)

if __name__ == "__main__":
    test_celery_flow()
