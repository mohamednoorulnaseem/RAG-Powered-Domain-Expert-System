# 🧠 ragcore

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688.svg)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4-412991.svg)
[![CI/CD Pipeline](https://github.com/mohamednoorulnaseem/RAG-Powered-Domain-Expert-System/actions/workflows/ci.yml/badge.svg)](https://github.com/mohamednoorulnaseem/RAG-Powered-Domain-Expert-System/actions)

RAG pipeline for document Q&A — LangChain · FAISS · FastAPI · Docker

## Overview
This repository provides a Retrieval-Augmented Generation (RAG) system for question answering over uploaded documents. It processes files (PDF, TXT, DOCX), splits them into recursive chunks, and indexes them in an in-memory FAISS vector database. When a user asks a query, the pipeline retrieves the most relevant context chunks and routes them to an LLM generator to construct a source-cited answer.

## Project Structure
```
ragcore/
├── api/
│   ├── __init__.py
│   └── main.py
├── config/
│   ├── __init__.py
│   └── settings.py
├── core/
│   ├── __init__.py
│   ├── document_processor.py
│   ├── embeddings.py
│   ├── query_engine.py
│   └── vector_store.py
├── dashboard/
│   ├── __init__.py
│   └── app.py
├── data/
├── docs/
├── logs/
├── scripts/
│   ├── __init__.py
│   ├── demo.py
│   ├── sample_contract.txt
│   └── test_suite.py
├── tests/
│   ├── __init__.py
│   └── test_api.py
├── uploads/
├── Dockerfile.api
├── Dockerfile.dashboard
├── docker-compose.yml
├── requirements.txt
├── requirements-dev.txt
└── pyproject.toml
```

## Tech Stack
- **API Framework**: FastAPI, Uvicorn
- **User Interface**: Streamlit
- **RAG Orchestration**: LangChain (PyPDF, docx2txt)
- **Vector Database**: FAISS (in-memory)
- **Embeddings & LLMs**: OpenAI (ada-002, GPT-4)
- **Containerization**: Docker, docker-compose

## Quick Start

### 1. Configure the Environment
Clone the repository and copy the environment template:
```bash
git clone https://github.com/mohamednoorulnaseem/RAG-Powered-Domain-Expert-System.git ragcore
cd ragcore
cp .env.example .env
```
Fill in your `OPENAI_API_KEY` inside `.env`.

### 2. Start the Stack (Docker Compose)
Launch the application components (FastAPI Backend + Streamlit Frontend) using Docker:
```bash
docker-compose up --build
```
Once initialized:
- **FastAPI API Documentation** is available at: `http://localhost:8000/docs`
- **Streamlit Dashboard** is available at: `http://localhost:8501`

### 3. API Usage Example
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

## Author
Mohamed Noor Ul Naseem
- **Email**: mohamednoorulnaseem@gmail.com
- **LinkedIn**: https://www.linkedin.com/in/mohamednoorulnaseem/
- **GitHub**: https://github.com/mohamednoorulnaseem
