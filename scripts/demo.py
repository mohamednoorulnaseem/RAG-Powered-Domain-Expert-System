"""
RAG Expert System - Demo Script
Demonstrates the complete RAG pipeline without the UI
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import DocumentProcessor, VectorStore, QueryEngine
from config import get_settings

# Check for API key
settings = get_settings()
if not settings.openai_api_key or settings.openai_api_key == "your-openai-api-key-here":
    print("\n" + "=" * 60)
    print("  ⚠️  SETUP REQUIRED: OpenAI API Key")
    print("=" * 60)
    print("\n  Please set your OpenAI API key in .env file:")
    print("  OPENAI_API_KEY=your-actual-key-here")
    print("\n  Get your key at: https://platform.openai.com/api-keys")
    print("=" * 60 + "\n")
    sys.exit(1)


def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")


def print_step(step_num, text):
    """Print a step indicator"""
    print(f"\n📍 Step {step_num}: {text}")
    print("-" * 40)


def demo():
    """Run the complete RAG demo"""

    print_header("🧠 RAG Expert System Demo")

    # Step 1: Initialize components
    print_step(1, "Initializing Components")

    processor = DocumentProcessor()
    print("  ✓ Document Processor ready")

    vector_store = VectorStore()
    print("  ✓ Vector Store ready")
    print(f"    └─ Current documents: {vector_store.collection.count()} chunks")

    query_engine = QueryEngine(vector_store=vector_store)
    print("  ✓ Query Engine ready")

    # Step 2: Check for sample document
    print_step(2, "Checking for Sample Documents")

    sample_doc = Path(__file__).parent / "sample_contract.txt"

    if sample_doc.exists():
        print(f"  ✓ Found sample document: {sample_doc.name}")

        # Process and ingest
        print("\n  Processing document...")
        processed = processor.process_document(str(sample_doc))
        print(f"    └─ Pages: {processed.num_pages}")
        print(f"    └─ Chunks: {processed.num_chunks}")

        print("\n  Storing in vector database...")
        result = vector_store.add_documents(processed.chunks)
        print(f"    └─ Stored: {result['added']} chunks")
        print(f"    └─ Total in DB: {result['collection_size']} chunks")
    else:
        print(f"  ⚠️ Sample document not found")
        print(f"     Create: {sample_doc}")

    # Step 3: Run sample queries
    print_step(3, "Running Sample Queries")

    sample_queries = [
        "What is the salary mentioned in the document?",
        "What are the termination terms?",
        "How much notice is required to end the contract?",
    ]

    if vector_store.collection.count() > 0:
        for i, query in enumerate(sample_queries, 1):
            print(f'\n  Query {i}: "{query}"')
            print("  " + "-" * 50)

            response = query_engine.query(query)

            print(f"  Answer: {response.answer[:300]}...")
            print(f"\n  📊 Metrics:")
            print(f"     └─ Confidence: {response.confidence}")
            print(f"     └─ Sources: {response.chunks_retrieved}")
            print(f"     └─ Time: {response.total_time_ms:.0f}ms")
    else:
        print("  ⚠️ No documents in vector store")
        print("     Upload documents first to run queries")

    # Step 4: Show statistics
    print_step(4, "System Statistics")

    stats = vector_store.get_stats()
    print(f"  Total Documents: {stats['total_documents']}")
    print(f"  Total Chunks: {stats['total_chunks']}")
    print(f"  Collection: {stats['collection_name']}")

    if stats["documents"]:
        print("\n  Indexed Documents:")
        for doc in stats["documents"]:
            print(f"    📄 {doc['source']}: {doc['chunks']} chunks")

    print_header("✅ Demo Complete!")
    print("  Start the full system with: start_all.bat")
    print("  Or use the API directly at: http://localhost:8000/docs\n")


if __name__ == "__main__":
    demo()
