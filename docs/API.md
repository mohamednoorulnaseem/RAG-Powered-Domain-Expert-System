# API Documentation

## Overview

The RAG Expert System API is a RESTful service built with FastAPI that provides document management and intelligent question-answering capabilities.

**Base URL:** `http://localhost:8001`

**API Documentation:** `http://localhost:8001/docs` (Interactive Swagger UI)

## Authentication

Currently, the API does not require authentication. For production deployments, implement proper authentication mechanisms.

## Endpoints

### Health Check

Check if the API is running and healthy.

**Endpoint:** `GET /health`

**Response:**

```json
{
  "status": "healthy",
  "timestamp": "2026-01-19T19:57:59",
  "version": "1.0.0",
  "components": {
    "api": "online",
    "vector_store": "online",
    "documents_indexed": 42
  }
}
```

---

### Upload Document

Upload a document for processing and indexing.

**Endpoint:** `POST /documents/upload`

**Content-Type:** `multipart/form-data`

**Parameters:**

- `file` (required): Document file (PDF, DOCX, TXT, MD)

**Example:**

```bash
curl -X POST "http://localhost:8001/documents/upload" \
  -F "file=@contract.pdf"
```

**Response:**

```json
{
  "success": true,
  "document": {
    "doc_id": "contract.pdf_a1b2c3d4",
    "filename": "contract.pdf",
    "file_type": ".pdf",
    "pages": 15,
    "chunks": 45
  },
  "indexing": {
    "added": 45,
    "collection_size": 87,
    "time_seconds": 3.2
  }
}
```

---

### Query Documents

Ask a question and get an AI-generated answer with citations.

**Endpoint:** `POST /query`

**Content-Type:** `application/json`

**Request Body:**

```json
{
  "question": "What is the termination notice period?",
  "top_k": 5,
  "min_score": 0.5,
  "session_id": "optional-session-id"
}
```

**Parameters:**

- `question` (required): The question to ask
- `top_k` (optional): Number of chunks to retrieve (default: 5)
- `min_score` (optional): Minimum similarity threshold (default: 0.5)
- `session_id` (optional): Session ID for conversation memory

**Response:**

```json
{
  "query": "What is the termination notice period?",
  "answer": "The termination notice period is 30 days written notice...",
  "citations": [
    {
      "source": "contract.pdf",
      "page": 3,
      "chunk": 2,
      "score": 0.92,
      "excerpt": "Either party may terminate with 30 days written notice..."
    }
  ],
  "confidence": "High",
  "metrics": {
    "search_time_ms": 45.2,
    "generation_time_ms": 1250.8,
    "total_time_ms": 1296.0,
    "chunks_retrieved": 5,
    "model": "gpt-4-turbo-preview"
  }
}
```

---

### List Documents

Get a list of all indexed documents.

**Endpoint:** `GET /documents`

**Response:**

```json
{
  "total": 3,
  "documents": [
    {
      "doc_id": "contract.pdf_a1b2c3d4",
      "source": "contract.pdf",
      "file_type": ".pdf",
      "chunks": 45
    }
  ]
}
```

---

### Get Document Details

Get detailed information about a specific document.

**Endpoint:** `GET /documents/{doc_id}`

**Response:**

```json
{
  "doc_id": "contract.pdf_a1b2c3d4",
  "source": "contract.pdf",
  "num_chunks": 45,
  "chunks": [
    {
      "chunk_id": "contract.pdf_p1_c1",
      "page": 1,
      "content_preview": "This Employment Agreement..."
    }
  ]
}
```

---

### Delete Document

Remove a document and all its chunks from the system.

**Endpoint:** `DELETE /documents/{doc_id}`

**Response:**

```json
{
  "success": true,
  "deleted_chunks": 45,
  "doc_id": "contract.pdf_a1b2c3d4"
}
```

---

### Search Chunks

Search for relevant chunks without generating an answer.

**Endpoint:** `GET /search?q=query&top_k=5`

**Parameters:**

- `q` (required): Search query
- `top_k` (optional): Number of results (default: 5)

**Response:**

```json
{
  "query": "termination",
  "results": [
    {
      "chunk_id": "contract.pdf_p3_c2",
      "source": "contract.pdf",
      "page": 3,
      "score": 0.92,
      "content": "Either party may terminate..."
    }
  ]
}
```

---

### Get Statistics

Get system-wide statistics.

**Endpoint:** `GET /stats`

**Response:**

```json
{
  "total_chunks": 87,
  "total_documents": 3,
  "collection_name": "in_memory",
  "documents": [
    {
      "doc_id": "contract.pdf_a1b2c3d4",
      "source": "contract.pdf",
      "file_type": ".pdf",
      "chunks": 45
    }
  ]
}
```

---

### Summarize Document

Generate a summary of a specific document.

**Endpoint:** `GET /documents/{doc_id}/summary`

**Response:**

```json
{
  "doc_id": "contract.pdf_a1b2c3d4",
  "source": "contract.pdf",
  "num_chunks": 45,
  "summary": "This employment contract outlines the terms..."
}
```

---

### Clear All Documents

Delete all documents from the system (use with caution).

**Endpoint:** `DELETE /clear`

**Response:**

```json
{
  "success": true,
  "deleted_chunks": 87,
  "message": "All documents have been removed"
}
```

---

## Error Handling

The API uses standard HTTP status codes:

- `200 OK`: Request successful
- `400 Bad Request`: Invalid request parameters
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

**Error Response Format:**

```json
{
  "detail": "Error message describing what went wrong"
}
```

---

## Rate Limiting

Currently, no rate limiting is implemented. For production use, implement appropriate rate limiting.

---

## Best Practices

1. **Upload Documents First**: Before querying, ensure documents are uploaded
2. **Use Session IDs**: For conversation context, use consistent session IDs
3. **Adjust Parameters**: Tune `top_k` and `min_score` based on your needs
4. **Handle Errors**: Always check response status and handle errors gracefully
5. **Monitor Performance**: Use the metrics in responses to optimize

---

## Examples

### Python Example

```python
import requests

# Upload document
with open('contract.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:8001/documents/upload',
        files={'file': f}
    )
print(response.json())

# Query
response = requests.post(
    'http://localhost:8001/query',
    json={
        'question': 'What is the salary?',
        'top_k': 5
    }
)
print(response.json()['answer'])
```

### JavaScript Example

```javascript
// Upload document
const formData = new FormData();
formData.append("file", fileInput.files[0]);

const uploadResponse = await fetch("http://localhost:8001/documents/upload", {
  method: "POST",
  body: formData,
});

// Query
const queryResponse = await fetch("http://localhost:8001/query", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    question: "What is the salary?",
    top_k: 5,
  }),
});

const result = await queryResponse.json();
console.log(result.answer);
```

---

## Interactive Documentation

For interactive API exploration, visit:
**http://localhost:8001/docs**

This provides a Swagger UI where you can test all endpoints directly in your browser.
