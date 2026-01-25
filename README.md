# 🧠 RAG-Powered Domain Expert System

![RAG Expert System Hero](docs/images/hero.png)

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688.svg)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4-412991.svg)
![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)
![Code Coverage](https://img.shields.io/badge/coverage-85%25-yellowgreen.svg)

Enterprise-grade Retrieval-Augmented Generation system for intelligent document analysis and question answering.

[Features](#features) | [Quick Start](#quick-start) | [Demo](#demo) | [Documentation](#support) | [Contributing](#contributing)

---

## Overview

Transform your documents into an intelligent knowledge base. This RAG system combines semantic search with large language models to provide accurate, source-cited answers without hallucinations.

**Perfect for:**

- Research teams analyzing large document collections
- Enterprises building internal knowledge bases
- Educational institutions creating learning assistants
- Legal/compliance teams searching regulatory documents

## Features

### Core Capabilities

- **Semantic Search**: OpenAI embeddings with vector similarity for precise document retrieval
- **AI-Powered Answers**: GPT-4 Turbo generates contextual responses with source citations
- **Multi-Format Support**: Process PDF, DOCX, TXT, and Markdown files
- **Modern Interface**: Beautiful Streamlit dashboard with real-time chat
- **RESTful API**: FastAPI backend with auto-generated documentation
- **Docker Ready**: One-command deployment with Docker Compose
- **Enterprise Security**: API key management and secure document handling
- **Analytics**: Track usage patterns and query performance

### Technical Features

- **Chunking Strategy**: Smart text segmentation with configurable overlap
- **Vector Database**: Efficient in-memory storage with persistence
- **Async Processing**: Non-blocking document uploads and queries
- **Error Handling**: Comprehensive error tracking and recovery
- **Logging**: Structured logging for debugging and monitoring

## Quick Start

### Prerequisites

- Python 3.10 or higher
- OpenAI API key ([Get one here](https://platform.openai.com/api-keys))
- 4GB RAM minimum

### Installation

#### Option 1: Quick Setup (Windows)

```batch
# 1. Clone repository
git clone https://github.com/mohamednoorulnaseem/RAG-Powered-Domain-Expert-System.git
cd RAG-Powered-Domain-Expert-System

# 2. Run automated setup
setup.bat

# 3. Configure API key
copy .env.example .env
# Edit .env and add: OPENAI_API_KEY=your-key-here

# 4. Start system
start.bat
```

#### Option 2: Docker (All Platforms)

```bash
# 1. Clone repository
git clone https://github.com/mohamednoorulnaseem/RAG-Powered-Domain-Expert-System.git
cd RAG-Powered-Domain-Expert-System

# 2. Configure environment
cp .env.example .env
# Edit .env with your API key

# 3. Start with Docker Compose
docker-compose up -d
```

#### Option 3: Manual Setup

```bash
# 1. Clone repository
git clone https://github.com/mohamednoorulnaseem/RAG-Powered-Domain-Expert-System.git
cd RAG-Powered-Domain-Expert-System

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your API key

# 5. Start API
uvicorn api.main:app --host 0.0.0.0 --port 8001 &

# 6. Start Dashboard
streamlit run dashboard/app.py
```

### Access Points

- **Dashboard**: <http://localhost:8501>
- **API**: <http://localhost:8001>
- **API Docs**: <http://localhost:8001/docs>

## Usage

### 1. Upload Documents

```python
# Via Dashboard: Drag and drop files
# Via API:
import requests

files = {'file': open('document.pdf', 'rb')}
response = requests.post('http://localhost:8001/api/v1/documents/upload', files=files)
```

### 2. Ask Questions

```python
# Via Dashboard: Type in chat interface
# Via API:
query = {
    "question": "What are the key findings?",
    "top_k": 5
}
response = requests.post('http://localhost:8001/api/v1/query', json=query)
```

### 3. Get Cited Answers

```json
{
  "answer": "The key findings include...",
  "sources": [
    {
      "content": "Relevant excerpt from document",
      "metadata": { "source": "document.pdf", "page": 5 },
      "similarity_score": 0.92
    }
  ]
}
```

## Architecture

```text
User --> Streamlit Dashboard --> FastAPI Backend --> Document Processor
                                      |                    |
                                      v                    v
                                 Query Engine <----> Vector Store
                                      |                    ^
                                      v                    |
                                  GPT-4 LLM         OpenAI Embeddings
```

### Component Details

- **API Layer**: FastAPI with async endpoints
- **Document Processing**: LangChain + PyPDF2/python-docx
- **Embeddings**: OpenAI text-embedding-3-large (3072 dimensions)
- **Vector Store**: In-memory FAISS with persistence
- **LLM**: GPT-4 Turbo with temperature=0.2 for consistency
- **Frontend**: Streamlit with custom components

## Project Structure

```text
rag-expert-system/
├── .github/workflows/      # CI/CD pipelines
├── api/                    # FastAPI application
├── core/                   # RAG components
├── dashboard/              # Streamlit app
├── config/                 # Configuration management
├── tests/                  # Test suite
├── docs/                   # Documentation
├── scripts/                # Utility scripts
├── docker-compose.yml      # Docker orchestration
├── Dockerfile.api          # API container
├── Dockerfile.dashboard    # Dashboard container
├── requirements.txt        # Python dependencies
└── README.md
```

## Configuration

Edit `.env` to customize:

```env
# OpenAI
OPENAI_API_KEY=sk-your-key-here
EMBEDDING_MODEL=text-embedding-3-large
LLM_MODEL=gpt-4-turbo-preview

# Chunking
CHUNK_SIZE=1000
CHUNK_OVERLAP=200

# Search
TOP_K_RESULTS=5
SIMILARITY_THRESHOLD=0.7

# Performance
MAX_WORKERS=4
BATCH_SIZE=10
```

## API Reference

### Upload Document

```bash
POST /api/v1/documents/upload
Content-Type: multipart/form-data

Response:
{
  "id": "doc_123",
  "filename": "document.pdf",
  "status": "processed"
}
```

### Query

```bash
POST /api/v1/query
Content-Type: application/json

{
  "question": "What is...?",
  "top_k": 5
}

Response:
{
  "answer": "...",
  "sources": [...],
  "processing_time": 1.23
}
```

For complete API documentation, visit `/docs` endpoint.

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test suite
pytest tests/test_api.py -v

# Run integration tests only
pytest -m integration
```

## Deployment

### Docker Deployment

```bash
docker-compose up -d
```

### Cloud Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for:

- AWS (ECS/Fargate)
- Google Cloud (Cloud Run)
- Azure (Container Instances)
- Kubernetes manifests

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Quick contribution workflow:**

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'feat: add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## Roadmap

- [ ] Multi-language support
- [ ] Advanced analytics dashboard
- [ ] Fine-tuning support for domain-specific models
- [ ] Integration with Pinecone/Weaviate
- [ ] Batch processing for large document sets
- [ ] User authentication and multi-tenancy
- [ ] Custom embedding models

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

### Mohamed Noorul Naseem

- Email: <noorulnaseem11@gmail.com>
- GitHub: [mohamednoorulnaseem](https://github.com/mohamednoorulnaseem)
- LinkedIn: [mohamednoorulnaseem](https://www.linkedin.com/in/mohamednoorulnaseem)

## 📧 Support

- **Quick Start**: [docs/QUICK_START.md](docs/QUICK_START.md)
- **Troubleshooting**: [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
- **API Reference**: [docs/API.md](docs/API.md)
- **Deployment**: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- **Issues**: [GitHub Issues](https://github.com/mohamednoorulnaseem/RAG-Powered-Domain-Expert-System/issues)
- **Discussions**: [GitHub Discussions](https://github.com/mohamednoorulnaseem/RAG-Powered-Domain-Expert-System/discussions)

---

### Built with Python, FastAPI, Streamlit & OpenAI

_If you find this project helpful, please consider giving it a star!_
