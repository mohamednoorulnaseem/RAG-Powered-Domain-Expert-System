import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.db import SessionLocal, Job, Attempt

def check_entries():
    db = SessionLocal()
    try:
        jobs = db.query(Job).all()
        print(f"Total Jobs in DB: {len(jobs)}")
        for j in jobs:
            print(f"Job ID: {j.job_id} | Status: {j.status} | Query: {j.original_query[:50]}")
            attempts = db.query(Attempt).filter(Attempt.job_id == j.job_id).all()
            print(f"  Attempts: {len(attempts)}")
            for a in attempts:
                print(f"    #{a.attempt_number} Score: F={a.faithfulness_score}, R={a.relevance_score}")
    except Exception as e:
        print(f"Error checking DB: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_entries()
