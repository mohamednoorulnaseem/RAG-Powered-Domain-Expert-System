import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime
from datasets import Dataset
from loguru import logger

# Configure stdout to use UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.document_processor import DocumentProcessor
from core.embeddings import HuggingFaceEmbeddingService
from core.vector_store import VectorStore
from core.query_engine import QueryEngine
from core.agent import SelfCorrectingRAGAgent
from config import get_settings

from dotenv import load_dotenv
load_dotenv()

# Configure environment fallback to Groq to bypass OpenAI requirement
groq_key = os.getenv("GROQ_API_KEY", "")
if not groq_key or "gsk_" not in groq_key:
    print("\nERROR: Valid GROQ_API_KEY is required to run local evaluations.")
    sys.exit(1)

# Route OpenAI-compatible calls to Groq
os.environ["OPENAI_API_KEY"] = groq_key
os.environ["OPENAI_BASE_URL"] = "https://api.groq.com/openai/v1"
os.environ["LLM_MODEL"] = "llama-3.1-8b-instant"

# Load settings
settings = get_settings()

QA_PAIRS = [
    {
        "question": "Who reports directly to the Chief Technology Officer?",
        "ground_truth": "The Senior Software Engineer (John Michael Smith) reports directly to the Chief Technology Officer."
    },
    {
        "question": "What is the annual base salary of the Employee?",
        "ground_truth": "$125,000 (One Hundred Twenty-Five Thousand Dollars)."
    },
    {
        "question": "Who is the Chief Executive Officer of TechCorp Industries?",
        "ground_truth": "Sarah Johnson."
    },
    {
        "question": "What is the position of John Michael Smith?",
        "ground_truth": "Senior Software Engineer."
    },
    {
        "question": "Where is the Company's headquarters located?",
        "ground_truth": "123 Innovation Drive, San Francisco, CA 94105."
    },
    {
        "question": "How many days of paid vacation does the employee receive per calendar year?",
        "ground_truth": "20 days of paid vacation."
    },
    {
        "question": "How many stock options is the employee granted?",
        "ground_truth": "Options to purchase 10,000 shares of the Company's common stock."
    },
    {
        "question": "What is the vesting period for the stock options?",
        "ground_truth": "Vesting over four years with a one-year cliff."
    },
    {
        "question": "What percentage of health, dental, and vision insurance premiums does the Company pay?",
        "ground_truth": "80% of premiums."
    },
    {
        "question": "What is the name of the Employee?",
        "ground_truth": "John Michael Smith."
    },
    {
        "question": "When was the Employment Agreement entered into?",
        "ground_truth": "January 1, 2024."
    },
    {
        "question": "What are the standard work hours specified in the contract?",
        "ground_truth": "Monday through Friday, 9:00 AM to 6:00 PM Pacific Time."
    },
    {
        "question": "What happens if TechCorp terminates the employment without Cause?",
        "ground_truth": "The Employee receives 3 months of base salary as severance, health insurance continue for 3 months, and vested options remain exercisable for 90 days."
    },
    {
        "question": "What is the duration of the non-compete restriction after termination?",
        "ground_truth": "Twelve (12) months following termination of employment."
    },
    {
        "question": "To whom does the Senior Software Engineer report?",
        "ground_truth": "Chief Technology Officer."
    },
    {
        "question": "Under what law is the agreement governed?",
        "ground_truth": "Laws of the State of California."
    },
    {
        "question": "Where does the arbitration take place in case of disputes?",
        "ground_truth": "San Francisco, California."
    },
    {
        "question": "How many paid holidays does the employee receive?",
        "ground_truth": "10 paid holidays."
    },
    {
        "question": "How many sick leave days are allowed per calendar year?",
        "ground_truth": "10 days of paid sick leave."
    },
    {
        "question": "What is the email address of the Employee?",
        "ground_truth": "john.smith@email.com."
    }
]

def run_evaluation():
    print("=" * 70)
    print("🚀 Running RAGAS Agentic RAG Evaluation (Phase 9)")
    print("=" * 70)
    
    # 1. Initialize local components
    print("\n[Step 1] Initializing pipeline with local HuggingFace embeddings...")
    processor = DocumentProcessor()
    embedding_service = HuggingFaceEmbeddingService()
    vector_store = VectorStore(embedding_service=embedding_service)
    
    # Clear and re-ingest sample contract to ensure clean database
    vector_store.clear()
    sample_doc_path = Path(__file__).parent / "sample_contract.txt"
    if not sample_doc_path.exists():
        print(f"Error: Sample contract not found at {sample_doc_path}")
        sys.exit(1)
        
    print(f"Ingesting sample contract: {sample_doc_path.name}")
    processed = processor.process_document(str(sample_doc_path))
    vector_store.add_documents(processed.chunks)
    
    query_engine = QueryEngine(vector_store=vector_store)
    agent = SelfCorrectingRAGAgent(query_engine=query_engine)
    
    # 2. Run queries
    print("\n[Step 2] Executing agent queries and capturing self-correction traces...")
    questions = []
    answers = []
    contexts = []
    ground_truths = []
    latencies = []
    attempts_counts = []
    
    for idx, item in enumerate(QA_PAIRS, 1):
        q = item["question"]
        gt = item["ground_truth"]
        print(f"[{idx}/20] Querying agent: {q}")
        
        start_t = time.time()
        result = agent.run(q)
        duration_ms = (time.time() - start_t) * 1000
        
        questions.append(q)
        answers.append(result["generation"])
        ground_truths.append(gt)
        contexts.append([doc["content"] for doc in result["reranked_docs"]])
        latencies.append(duration_ms)
        attempts_counts.append(result["attempts"])
        
        print(f"      Attempts: {result['attempts']} | Time: {duration_ms/1000:.2f}s")
        # Slight pause to prevent rate limits
        time.sleep(0.5)
        
    # 3. Ragas evaluation setup
    print("\n[Step 3] Running Ragas Evaluation...")
    dataset = Dataset.from_dict({
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truths
    })
    
    # Configure custom wrappers for Ragas
    from ragas import evaluate
    from ragas.llms import LangchainLLMWrapper
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from langchain_groq import ChatGroq
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from ragas.metrics import Faithfulness, AnswerRelevancy
    from ragas.run_config import RunConfig
    
    # Wrapper instances
    groq_llm = ChatGroq(model="llama-3.1-8b-instant", groq_api_key=groq_key, temperature=0.0)
    ragas_llm = LangchainLLMWrapper(groq_llm)
    local_emb = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    ragas_embeddings = LangchainEmbeddingsWrapper(local_emb)
    
    # Initialize metrics
    faithfulness_metric = Faithfulness()
    relevancy_metric = AnswerRelevancy(strictness=1)
    
    run_config = RunConfig(max_workers=1)
    
    results = evaluate(
        dataset=dataset,
        metrics=[faithfulness_metric, relevancy_metric],
        llm=ragas_llm,
        embeddings=ragas_embeddings,
        run_config=run_config
    )
    
    scores = results._repr_dict
    avg_faithfulness = scores.get("faithfulness", 0.0)
    avg_relevancy = scores.get("answer_relevancy", 0.0)
    avg_latency = sum(latencies) / len(latencies)
    avg_attempts = sum(attempts_counts) / len(attempts_counts)
    
    print("\n" + "=" * 70)
    print("📊 AGENTIC RAG SYSTEM EVALUATION RESULTS")
    print("=" * 70)
    print(f"Average Faithfulness Score: {avg_faithfulness:.4f}")
    print(f"Average Answer Relevancy   : {avg_relevancy:.4f}")
    print(f"Average Query Latency      : {avg_latency:.2f}ms")
    print(f"Average Attempts Needed    : {avg_attempts:.2f}")
    
    # 4. Save results to metrics/agent.json
    output_dir = Path(__file__).parent.parent / "docs" / "metrics"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_data = {
        "timestamp": datetime.now().isoformat(),
        "average_faithfulness": avg_faithfulness,
        "average_relevancy": avg_relevancy,
        "average_latency_ms": avg_latency,
        "average_attempts": avg_attempts,
        "scores": scores,
        "detailed_results": [
            {
                "question": q,
                "answer": ans,
                "ground_truth": gt,
                "latency_ms": lat,
                "attempts": att
            }
            for q, ans, gt, lat, att in zip(questions, answers, ground_truths, latencies, attempts_counts)
        ]
    }
    
    with open(output_dir / "agent.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)
        
    # 5. Output comparative metrics table
    print("\n" + "=" * 70)
    print("🏁 COMPARATIVE PERFORMANCE REPORT")
    print("=" * 70)
    print(f"{'Metric':<25} | {'Baseline':<10} | {'Reranked':<10} | {'Agentic Loop':<12}")
    print("-" * 70)
    print(f"{'Faithfulness':<25} | {'0.6263':<10} | {'0.6663':<10} | {avg_faithfulness:<12.4f}")
    print(f"{'Answer Relevancy':<25} | {'0.7239':<10} | {'0.7231':<10} | {avg_relevancy:<12.4f}")
    print(f"{'Avg Latency (ms)':<25} | {'~1500':<10} | {'~2200':<10} | {avg_latency:<12.1f}")
    print(f"{'Avg Attempts':<25} | {'1.00':<10} | {'1.00':<10} | {avg_attempts:<12.2f}")
    print("=" * 70)
    print("Comparative report successfully compiled and saved to docs/metrics/agent.json.")

if __name__ == "__main__":
    run_evaluation()
