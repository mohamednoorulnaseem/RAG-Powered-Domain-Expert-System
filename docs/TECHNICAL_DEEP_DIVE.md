# RAG Expert System - Technical Deep Dive

## 🔬 Core Concepts Explained

### 1. Vector Embeddings

**What are embeddings?**
Embeddings are numerical representations of text that capture semantic meaning. They convert words and sentences into vectors (lists of numbers) in a high-dimensional space.

**How it works:**

```python
# Input text
text = "Employment termination requires 30 days notice"

# OpenAI returns 3072 floating-point numbers
embedding = openai.embeddings.create(
    model="text-embedding-3-large",
    input=text
).data[0].embedding

# Result: [0.0023, -0.0891, 0.0456, ..., 0.0123]
# Length: 3072 dimensions
```

**Why it's powerful:**

- Similar concepts have similar vectors
- "termination" ≈ "resignation" ≈ "end of contract"
- Mathematical operations can find semantic similarity

### 2. Cosine Similarity

**Formula:**

```
similarity = (A · B) / (||A|| × ||B||)
           = Σ(Ai × Bi) / (√Σ(Ai²) × √Σ(Bi²))
```

**In code:**

```python
import numpy as np

def cosine_similarity(vec1, vec2):
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    return dot_product / (norm1 * norm2)

# Example
similarity = cosine_similarity(question_embedding, chunk_embedding)
# Returns: 0.0 to 1.0 (higher = more similar)
```

### 3. Chunking Strategy

**Why chunk documents?**

- LLMs have token limits (GPT-4: 128K, but context matters)
- Smaller chunks = more precise retrieval
- Overlap prevents information loss at boundaries

**Optimal settings:**

```python
chunk_size = 1000      # Characters per chunk
chunk_overlap = 200    # Characters of overlap

# Recursive splitting prioritizes:
# 1. Paragraphs ("\n\n")
# 2. Sentences ("\n")
# 3. Words (" ")
```

### 4. Vector Database (ChromaDB)

**Why ChromaDB?**

- Local (no external service needed)
- Persistent storage
- Fast approximate nearest neighbor (ANN) search
- Free and open source

**How it stores data:**

```
┌─────────────────────────────────────────────────────┐
│                    ChromaDB                         │
├─────────────────────────────────────────────────────┤
│ ID          │ Embedding (3072d) │ Metadata          │
├─────────────┼───────────────────┼───────────────────┤
│ chunk_001   │ [0.02, -0.89...]  │ {source, page}    │
│ chunk_002   │ [0.15, 0.34...]   │ {source, page}    │
│ chunk_003   │ [-0.23, 0.67...]  │ {source, page}    │
└─────────────────────────────────────────────────────┘
```

---

## 🏗️ System Components Deep Dive

### Document Processor (`core/document_processor.py`)

**Responsibilities:**

1. Load documents (PDF, DOCX, TXT, MD)
2. Extract text content
3. Split into chunks
4. Add metadata (page numbers, chunk IDs)

**Key classes:**

```python
@dataclass
class ProcessedDocument:
    doc_id: str           # Unique identifier
    filename: str         # Original filename
    num_pages: int        # Total pages
    num_chunks: int       # Total chunks created
    chunks: List[Document]  # LangChain Document objects
    checksum: str         # MD5 hash for deduplication
```

### Embedding Service (`core/embeddings.py`)

**Supports two backends:**

1. **OpenAI (recommended):**
   - Higher quality embeddings
   - 3072 dimensions (text-embedding-3-large)
   - Cost: ~$0.0001 per 1K tokens

2. **HuggingFace (free):**
   - Runs locally
   - 384 dimensions (all-MiniLM-L6-v2)
   - No API costs

### Vector Store (`core/vector_store.py`)

**Key operations:**

```python
# Add documents
vector_store.add_documents(chunks)

# Search (returns top K similar chunks)
results = vector_store.search(
    query="What is the salary?",
    top_k=5,
    min_score=0.7
)

# Get document stats
stats = vector_store.get_stats()
```

### Query Engine (`core/query_engine.py`)

**The RAG orchestrator:**

1. Converts question to embedding
2. Searches vector database
3. Builds context from results
4. Generates answer with GPT-4
5. Formats response with citations

**Response structure:**

```python
@dataclass
class QueryResponse:
    query: str                    # Original question
    answer: str                   # Generated answer
    citations: List[Citation]     # Source references
    confidence: str               # High/Medium/Low
    search_time_ms: float         # Vector search time
    generation_time_ms: float     # LLM generation time
    total_time_ms: float          # Total response time
```

---

## 🔧 Configuration Options

### Environment Variables

| Variable               | Default                | Description              |
| ---------------------- | ---------------------- | ------------------------ |
| `OPENAI_API_KEY`       | (required)             | Your OpenAI API key      |
| `EMBEDDING_MODEL`      | text-embedding-3-large | OpenAI embedding model   |
| `LLM_MODEL`            | gpt-4-turbo-preview    | Chat completion model    |
| `CHUNK_SIZE`           | 1000                   | Characters per chunk     |
| `CHUNK_OVERLAP`        | 200                    | Overlap between chunks   |
| `TOP_K_RESULTS`        | 5                      | Chunks to retrieve       |
| `SIMILARITY_THRESHOLD` | 0.7                    | Minimum similarity score |

### Prompt Engineering

**System prompt (what the AI "is"):**

```
You are an expert document analyst assistant. Your role is to provide
accurate, comprehensive answers based ONLY on the provided context from
uploaded documents...
```

**Query prompt (how to answer):**

```
Based on the following context from uploaded documents, please answer the question.

CONTEXT:
{context}

QUESTION: {question}

INSTRUCTIONS:
- Answer based ONLY on the context provided above
- If the answer is not in the context, say "I cannot find this information"
- Cite specific sources when possible
```

---

## 📊 Performance Optimization

### 1. Caching (Redis)

```python
# Enable in .env
REDIS_URL=redis://localhost:6379

# Caches:
# - Query embeddings (avoid re-computing)
# - Frequent query results (instant responses)
```

### 2. Batch Processing

```python
# Process multiple chunks at once
embeddings = embedding_service.embed_texts(
    texts=chunks,
    batch_size=100  # OpenAI handles batches efficiently
)
```

### 3. Hybrid Search (Future)

Combine vector search with keyword search for best results:

```python
def hybrid_search(query):
    vector_results = vector_search(query)    # Semantic
    keyword_results = bm25_search(query)      # Exact match
    return rerank(vector_results + keyword_results)
```

---

## 🔒 Security Considerations

### API Key Protection

- Never commit `.env` to version control
- Use environment variables in production
- Rotate keys periodically

### Data Privacy

- Documents stored locally (ChromaDB)
- No data sent to external services except:
  - OpenAI (for embeddings and chat)
- Consider local LLM (Ollama) for sensitive data

### Input Validation

- File size limits (default: 50MB)
- Allowed extensions only
- Sanitized filenames

---

## 🐛 Debugging Tips

### Check Vector Store Contents

```python
# In Python shell
from core import VectorStore
vs = VectorStore()
print(vs.get_stats())
```

### Test Embedding Similarity

```python
from core import get_embedding_service

service = get_embedding_service()
emb1 = service.embed_text("termination clause")
emb2 = service.embed_text("end of contract")

from core.embeddings import cosine_similarity
print(f"Similarity: {cosine_similarity(emb1, emb2):.2%}")
```

### View Retrieved Chunks (Before LLM)

```python
from core import QueryEngine
qe = QueryEngine()
chunks = qe.get_similar_chunks("What is the salary?", top_k=5)
for c in chunks:
    print(f"Score: {c['score']:.2f} - {c['content'][:100]}...")
```

---

## 📈 Scaling Considerations

### For Production

| Aspect    | Development      | Production                  |
| --------- | ---------------- | --------------------------- |
| Vector DB | ChromaDB (local) | Pinecone, Weaviate          |
| LLM       | OpenAI API       | OpenAI + rate limiting      |
| Caching   | None             | Redis                       |
| API       | Single process   | Gunicorn + multiple workers |
| Storage   | Local disk       | S3, GCS                     |

### Estimated Limits

| Resource         | Current Limit | Scalable To          |
| ---------------- | ------------- | -------------------- |
| Documents        | ~1000         | 100,000+ (Pinecone)  |
| Concurrent users | ~10           | 1000+ (with scaling) |
| Query latency    | 2-3s          | <1s (caching)        |

---

This technical documentation should help you understand every aspect of the RAG Expert System! 🚀
