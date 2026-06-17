"""
RAG Expert System - Reranked Evaluation
Evaluates the updated two-stage RAG pipeline (with Cross-Encoder reranking) using Ragas metrics on the same 20 QA pairs.
"""

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

# Define 20 Question-Ground Truth pairs based on sample_contract.txt
QA_PAIRS = [
    {
        "question": "Who reports directly to the Chief Technology Officer?",
        "ground_truth": "The Senior Software Engineer (John Michael Smith) reports directly to the Chief Technology Officer.",
    },
    {
        "question": "What is the annual base salary of the Employee?",
        "ground_truth": "$125,000 (One Hundred Twenty-Five Thousand Dollars).",
    },
    {
        "question": "Who is the Chief Executive Officer of TechCorp Industries?",
        "ground_truth": "Sarah Johnson.",
    },
    {
        "question": "What is the position of John Michael Smith?",
        "ground_truth": "Senior Software Engineer.",
    },
    {
        "question": "Where is the Company's headquarters located?",
        "ground_truth": "123 Innovation Drive, San Francisco, CA 94105.",
    },
    {
        "question": "How many days of paid vacation does the employee receive per calendar year?",
        "ground_truth": "20 days of paid vacation.",
    },
    {
        "question": "How many stock options is the employee granted?",
        "ground_truth": "Options to purchase 10,000 shares of the Company's common stock.",
    },
    {
        "question": "What is the vesting period for the stock options?",
        "ground_truth": "Vesting over four years with a one-year cliff.",
    },
    {
        "question": "What percentage of health, dental, and vision insurance premiums does the Company pay?",
        "ground_truth": "80% of premiums.",
    },
    {
        "question": "What is the name of the Employee?",
        "ground_truth": "John Michael Smith.",
    },
    {
        "question": "When was the Employment Agreement entered into?",
        "ground_truth": "January 1, 2024.",
    },
    {
        "question": "What are the standard work hours specified in the contract?",
        "ground_truth": "Monday through Friday, 9:00 AM to 6:00 PM Pacific Time.",
    },
    {
        "question": "What happens if TechCorp terminates the employment without Cause?",
        "ground_truth": "The Employee receives 3 months of base salary as severance, health insurance continue for 3 months, and vested options remain exercisable for 90 days.",
    },
    {
        "question": "What is the duration of the non-compete restriction after termination?",
        "ground_truth": "Twelve (12) months following termination of employment.",
    },
    {
        "question": "To whom does the Senior Software Engineer report?",
        "ground_truth": "Chief Technology Officer.",
    },
    {
        "question": "Under what law is the agreement governed?",
        "ground_truth": "Laws of the State of California.",
    },
    {
        "question": "Where does the arbitration take place in case of disputes?",
        "ground_truth": "San Francisco, California.",
    },
    {
        "question": "How many paid holidays does the employee receive?",
        "ground_truth": "10 paid holidays.",
    },
    {
        "question": "How many sick leave days are allowed per calendar year?",
        "ground_truth": "10 days of paid sick leave.",
    },
    {
        "question": "What is the email address of the Employee?",
        "ground_truth": "john.smith@email.com.",
    },
]


def run_evaluation():
    print("=" * 70)
    print("🚀 Running RAGAS Reranked Evaluation")
    print("=" * 70)

    # 1. Initialize local components
    print(
        "\n[Step 1] Initializing pipeline with local HuggingFace embeddings and reranker..."
    )
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

    # 2. Run queries
    print("\n[Step 2] Executing queries and capturing context...")
    questions = []
    answers = []
    contexts = []
    ground_truths = []
    latencies = []

    for idx, item in enumerate(QA_PAIRS, 1):
        q = item["question"]
        gt = item["ground_truth"]
        print(f"[{idx}/20] Querying (Reranked): {q}")

        start_t = time.time()
        response = query_engine.query(q)
        duration_ms = (time.time() - start_t) * 1000

        questions.append(q)
        answers.append(response.answer)
        ground_truths.append(gt)
        # Retrieve context chunk texts
        contexts.append([c.excerpt for c in response.citations])
        latencies.append(duration_ms)

        # Slight pause to prevent rate limits
        time.sleep(0.5)

    # 3. Ragas evaluation setup
    print("\n[Step 3] Running Ragas Evaluation...")
    dataset = Dataset.from_dict(
        {
            "question": questions,
            "answer": answers,
            "contexts": contexts,
            "ground_truth": ground_truths,
        }
    )

    # Configure custom wrappers for Ragas
    from ragas import evaluate
    from ragas.llms import LangchainLLMWrapper
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from langchain_groq import ChatGroq
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from ragas.metrics import Faithfulness, AnswerRelevancy
    from ragas.run_config import RunConfig

    # Wrapper instances
    groq_llm = ChatGroq(
        model="llama-3.1-8b-instant", groq_api_key=groq_key, temperature=0.0
    )
    ragas_llm = LangchainLLMWrapper(groq_llm)

    local_emb = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    ragas_embeddings = LangchainEmbeddingsWrapper(local_emb)

    # Use AnswerRelevancy with strictness=1 to bypass the n > 1 choice constraint on Groq
    metrics = [Faithfulness(), AnswerRelevancy(strictness=1)]
    run_config = RunConfig(max_workers=1)

    try:
        eval_result = evaluate(
            dataset=dataset,
            metrics=metrics,
            llm=ragas_llm,
            embeddings=ragas_embeddings,
            run_config=run_config,
        )
    except Exception as e:
        print(f"Ragas evaluation failed: {e}")
        sys.exit(1)

    # 4. Save and output metrics
    scores_dict = getattr(eval_result, "_repr_dict", {})
    avg_faithfulness = scores_dict.get("faithfulness", 0.0)
    avg_relevancy = scores_dict.get("answer_relevancy", 0.0)
    avg_latency_ms = sum(latencies) / len(latencies)

    results_data = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "avg_faithfulness": round(float(avg_faithfulness), 4),
            "avg_relevancy": round(float(avg_relevancy), 4),
            "avg_latency_ms": round(float(avg_latency_ms), 2),
        },
        "queries": [],
    }

    # Package details
    for i in range(len(questions)):
        results_data["queries"].append(
            {
                "question": questions[i],
                "answer": answers[i],
                "ground_truth": ground_truths[i],
                "latency_ms": round(latencies[i], 2),
            }
        )

    # Create docs/metrics directory if not exists
    metrics_dir = Path("docs/metrics")
    metrics_dir.mkdir(parents=True, exist_ok=True)

    output_file = metrics_dir / "after_reranking.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results_data, f, indent=2)

    # Print clean results table
    print("\n" + "=" * 70)
    print("📈 EVALUATION RESULTS TABLE (AFTER RERANKING)")
    print("=" * 70)
    print(f"| Metric               | Value       |")
    print(f"|----------------------|-------------|")
    print(f"| Avg Faithfulness     | {avg_faithfulness:.4f}      |")
    print(f"| Avg Answer Relevancy | {avg_relevancy:.4f}      |")
    print(f"| Avg Latency (ms)     | {avg_latency_ms:.2f} ms   |")
    print("=" * 70)
    print(f"Results successfully saved to {output_file}\n")


if __name__ == "__main__":
    run_evaluation()
