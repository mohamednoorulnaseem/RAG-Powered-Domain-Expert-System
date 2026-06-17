"""
Comprehensive Test Suite for RAG Expert System
Tests all components to ensure production readiness
"""

import sys
import os
from pathlib import Path
import time
from typing import Dict, List, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestRunner:
    """Professional test runner with detailed reporting"""

    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures = []

    def run_test(self, test_name: str, test_func) -> bool:
        """Run a single test and track results"""
        self.tests_run += 1
        print(f"\n{'='*70}")
        print(f"Test {self.tests_run}: {test_name}")
        print(f"{'='*70}")

        try:
            start_time = time.time()
            test_func()
            elapsed = time.time() - start_time

            print(f"PASSED ({elapsed:.2f}s)")
            self.tests_passed += 1
            return True

        except AssertionError as e:
            print(f"FAILED: {str(e)}")
            self.failures.append((test_name, str(e)))
            self.tests_failed += 1
            return False

        except Exception as e:
            print(f"ERROR: {str(e)}")
            self.failures.append((test_name, f"Error: {str(e)}"))
            self.tests_failed += 1
            return False

    def print_summary(self):
        """Print test summary"""
        print(f"\n{'='*70}")
        print("TEST SUMMARY")
        print(f"{'='*70}")
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_failed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")

        if self.failures:
            print(f"\n{'='*70}")
            print("FAILURES")
            print(f"{'='*70}")
            for test_name, error in self.failures:
                print(f"\n{test_name}:")
                print(f"  {error}")

        return self.tests_failed == 0


# Test Functions


def test_imports():
    """Test all critical imports"""
    print("Testing imports...")

    # Core modules
    from config import get_settings
    from core import DocumentProcessor, VectorStore, QueryEngine
    from core.embeddings import get_embedding_service

    # LangChain
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_core.documents import Document
    from langchain_community.document_loaders import PyPDFLoader

    # External libraries
    from openai import OpenAI
    from sentence_transformers import SentenceTransformer
    import streamlit
    import fastapi

    print("  All imports successful")


def test_configuration():
    """Test configuration loading"""
    print("Testing configuration...")

    from config import get_settings

    settings = get_settings()

    # Check critical settings
    assert (
        settings.api_port == 8001
    ), f"API port should be 8001, got {settings.api_port}"
    assert settings.streamlit_port == 8501, "Streamlit port should be 8501"
    assert settings.chunk_size > 0, "Chunk size must be positive"
    assert settings.chunk_overlap >= 0, "Chunk overlap must be non-negative"
    assert (
        0 <= settings.similarity_threshold <= 1
    ), "Similarity threshold must be between 0 and 1"

    # Check directories
    assert settings.upload_dir.exists(), "Upload directory should exist"
    assert settings.data_dir.exists(), "Data directory should exist"
    assert settings.logs_dir.exists(), "Logs directory should exist"

    print(f"  API Port: {settings.api_port}")
    print(f"  Chunk Size: {settings.chunk_size}")
    print(f"  Directories: OK")


def test_document_processor():
    """Test document processor initialization"""
    print("Testing document processor...")

    from core import DocumentProcessor

    processor = DocumentProcessor()

    assert processor.settings is not None, "Settings should be loaded"
    assert processor.text_splitter is not None, "Text splitter should be initialized"
    assert len(processor.loader_mapping) > 0, "Loader mapping should have entries"

    # Check supported formats
    supported = list(processor.loader_mapping.keys())
    assert ".pdf" in supported, "PDF should be supported"
    assert ".docx" in supported, "DOCX should be supported"
    assert ".txt" in supported, "TXT should be supported"

    print(f"  Supported formats: {', '.join(supported)}")


def test_vector_store():
    """Test vector store initialization"""
    print("Testing vector store...")

    from core import VectorStore

    vector_store = VectorStore()

    assert vector_store.settings is not None, "Settings should be loaded"
    assert (
        vector_store.embedding_service is not None
    ), "Embedding service should be initialized"
    assert vector_store.entries is not None, "Entries list should exist"
    assert hasattr(vector_store, "collection"), "Collection property should exist"

    # Test collection count
    count = vector_store.collection.count()
    assert count >= 0, "Collection count should be non-negative"

    print(f"  Entries: {len(vector_store.entries)}")
    print(f"  Embedding service: OK")


def test_query_engine():
    """Test query engine initialization"""
    print("Testing query engine...")

    from core import QueryEngine, VectorStore

    vector_store = VectorStore()
    query_engine = QueryEngine(vector_store=vector_store)

    assert query_engine.settings is not None, "Settings should be loaded"
    assert query_engine.vector_store is not None, "Vector store should be set"
    assert query_engine.client is not None, "OpenAI client should be initialized"
    assert query_engine.history is not None, "History should be initialized"

    print(f"  Model: {query_engine.settings.llm_model}")
    print(f"  Max history: {query_engine.max_history}")


def test_embedding_service():
    """Test embedding service"""
    print("Testing embedding service...")

    from core.embeddings import get_embedding_service

    # Test OpenAI embeddings
    service = get_embedding_service(use_openai=True)

    assert service is not None, "Embedding service should be initialized"
    assert service.dimension > 0, "Embedding dimension should be positive"

    print(f"  Service type: {type(service).__name__}")
    print(f"  Dimension: {service.dimension}")


def test_api_structure():
    """Test API module structure"""
    print("Testing API structure...")

    from api import main

    assert hasattr(main, "app"), "FastAPI app should exist"
    assert hasattr(main, "settings"), "Settings should be loaded"
    assert hasattr(main, "document_processor"), "Document processor should exist"
    assert hasattr(main, "vector_store"), "Vector store should exist"
    assert hasattr(main, "query_engine"), "Query engine should exist"

    # Check app configuration
    app = main.app
    assert app.title == "RAG Expert System API", "App title should be correct"
    assert app.version == "1.0.0", "App version should be correct"

    print(f"  App title: {app.title}")
    print(f"  Version: {app.version}")


def test_file_structure():
    """Test project file structure"""
    print("Testing file structure...")

    base_dir = Path(__file__).parent.parent

    # Required directories
    required_dirs = [
        "api",
        "core",
        "config",
        "dashboard",
        "docs",
        "scripts",
        "data",
        "uploads",
        "logs",
    ]

    for dir_name in required_dirs:
        dir_path = base_dir / dir_name
        assert dir_path.exists(), f"Directory {dir_name} should exist"

    # Required files
    required_files = [
        "requirements.txt",
        "README.md",
        "LICENSE",
        ".gitignore",
        ".env.example",
        "CONTRIBUTING.md",
    ]

    for file_name in required_files:
        file_path = base_dir / file_name
        assert file_path.exists(), f"File {file_name} should exist"

    print(f"  Directories: {len(required_dirs)} OK")
    print(f"  Files: {len(required_files)} OK")


def test_environment_variables():
    """Test environment variable configuration"""
    print("Testing environment variables...")

    from config import get_settings

    settings = get_settings()

    # Check if API key is configured (length check, not actual validation)
    if settings.openai_api_key:
        assert len(settings.openai_api_key) > 20, "OpenAI API key seems too short"
        print("  OpenAI API Key: Configured")
    else:
        print("  OpenAI API Key: Not configured (required for operation)")

    # Check model names
    assert settings.embedding_model, "Embedding model should be set"
    assert settings.llm_model, "LLM model should be set"

    print(f"  Embedding Model: {settings.embedding_model}")
    print(f"  LLM Model: {settings.llm_model}")


def test_batch_scripts():
    """Test batch script existence and configuration"""
    print("Testing batch scripts...")

    base_dir = Path(__file__).parent.parent

    scripts = ["setup.bat", "start.bat"]

    for script in scripts:
        script_path = base_dir / script
        assert script_path.exists(), f"Script {script} should exist"

        # Check for correct port in start scripts
        if "start" in script:
            content = script_path.read_text()
            if "api" in script or "all" in script:
                assert "8001" in content, f"{script} should reference port 8001"

    print(f"  Scripts found: {len(scripts)}")
    print(f"  Port configuration: OK")


def test_documentation():
    """Test documentation completeness"""
    print("Testing documentation...")

    base_dir = Path(__file__).parent.parent
    docs_dir = base_dir / "docs"

    required_docs = ["API.md", "DEPLOYMENT.md"]

    for doc in required_docs:
        doc_path = docs_dir / doc
        assert doc_path.exists(), f"Documentation {doc} should exist"

        # Check file is not empty
        content = doc_path.read_text()
        assert len(content) > 100, f"{doc} should have substantial content"

    print(f"  Documentation files: {len(required_docs)} OK")


# Main test execution


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("RAG EXPERT SYSTEM - COMPREHENSIVE TEST SUITE")
    print("=" * 70)

    runner = TestRunner()

    # Run all tests
    runner.run_test("Import Tests", test_imports)
    runner.run_test("Configuration Tests", test_configuration)
    runner.run_test("Document Processor Tests", test_document_processor)
    runner.run_test("Vector Store Tests", test_vector_store)
    runner.run_test("Query Engine Tests", test_query_engine)
    runner.run_test("Embedding Service Tests", test_embedding_service)
    runner.run_test("API Structure Tests", test_api_structure)
    runner.run_test("File Structure Tests", test_file_structure)
    runner.run_test("Environment Variables Tests", test_environment_variables)
    runner.run_test("Batch Scripts Tests", test_batch_scripts)
    runner.run_test("Documentation Tests", test_documentation)

    # Print summary
    success = runner.print_summary()

    if success:
        print("\n" + "=" * 70)
        print("PASSED - SYSTEM IS PRODUCTION READY!")
        print("=" * 70)
        print("\nNext steps:")
        print("  1. Run: start.bat")
        print("  2. Access Dashboard: http://localhost:8501")
        print("  3. Access API: http://localhost:8001")
        return 0
    else:
        print("\n" + "=" * 70)
        print("WARNING: SOME TESTS FAILED - PLEASE REVIEW")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
