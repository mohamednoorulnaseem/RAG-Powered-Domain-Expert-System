"""
API Integration Tests
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from pathlib import Path
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.main import app

@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def sample_document():
    """Sample document for testing"""
    return {
        "content": "This is a test document about machine learning.",
        "metadata": {
            "source": "test.txt",
            "page": 1
        }
    }


class TestGeneralEndpoints:
    """Test general API endpoints"""
    
    def test_root(self, client):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "running"

    def test_health_check(self, client):
        """Test health endpoint returns 200"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestDocumentEndpoints:
    """Test document management functionality"""
    
    def test_list_documents(self, client):
        """Test listing documents"""
        response = client.get("/documents")
        assert response.status_code == 200
        assert "documents" in response.json()
    
    def test_get_stats(self, client):
        """Test stats endpoint"""
        response = client.get("/stats")
        assert response.status_code == 200
        assert "total_chunks" in response.json()


@pytest.mark.unit
class TestCoreComponents:
    """Test core RAG components via mocking"""
    
    def test_document_processor_init(self):
        """Test document processor initialization"""
        from core.document_processor import DocumentProcessor
        processor = DocumentProcessor()
        assert processor.settings is not None
        assert ".pdf" in processor.loader_mapping

    def test_vector_store_init(self):
        """Test vector store initialization"""
        from core.vector_store import VectorStore
        # Mock embedding service to avoid API calls
        with patch('core.embeddings.OpenAIEmbeddingService') as mock_service:
            store = VectorStore(embedding_service=mock_service.return_value)
            assert store.entries == []
            assert store.persist_path is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
