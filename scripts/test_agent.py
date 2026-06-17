import os
import sys
from pathlib import Path
from dotenv import load_dotenv

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

load_dotenv()


def test_agent_run():
    print("=" * 70)
    print("🤖 Testing Self-Correcting RAG Agent")
    print("=" * 70)

    # 1. Initialize components and ingest sample document
    processor = DocumentProcessor()
    embedding_service = HuggingFaceEmbeddingService()
    vector_store = VectorStore(embedding_service=embedding_service)

    # Ingest the contract to make sure vector store is populated
    sample_doc_path = Path(__file__).parent / "sample_contract.txt"
    if not sample_doc_path.exists():
        print(f"Error: Sample contract not found at {sample_doc_path}")
        sys.exit(1)

    print(f"Populating vector store with: {sample_doc_path.name}...")
    vector_store.clear()
    processed = processor.process_document(str(sample_doc_path))
    vector_store.add_documents(processed.chunks)

    query_engine = QueryEngine(vector_store=vector_store)

    # 2. Initialize Agent
    agent = SelfCorrectingRAGAgent(query_engine=query_engine)

    # 3. Define a query
    query = "Who is John Michael Smith reporting to and what is his options vesting?"

    print(f"\nRunning agent for query: '{query}'")
    result = agent.run(query)

    print("\n" + "=" * 70)
    print("🏁 FINAL AGENT RESPONSE")
    print("=" * 70)
    print(result["generation"])
    print("\n" + "=" * 70)
    print("📊 ATTEMPTS HISTORIES")
    print("=" * 70)
    for hist in result.get("history", []):
        print(f"Attempt: {hist['attempt']}")
        print(f"  Query used   : {hist['query']}")
        print(f"  Faithfulness : {hist['faithfulness']:.4f}")
        print(f"  Relevancy    : {hist['relevancy']:.4f}")
        print("-" * 50)

    print(
        f"Final scores -> Faithfulness: {result['faithfulness_score']:.4f}, Relevancy: {result['answer_relevance_score']:.4f}"
    )
    print(f"Total attempts: {result['attempts']}")
    print("=" * 70)


if __name__ == "__main__":
    test_agent_run()
