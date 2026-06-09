# 🧠 RAG-Powered Domain Expert System

A production-ready document intelligence system where you upload any document (PDF, TXT, DOCX) and ask questions in plain English. The system uses vector similarity search (FAISS) to find the most relevant content and generates accurate, grounded answers using GPT-4o — with source citations and zero hallucinations. Answers come only from your uploaded documents.

---

## ✨ Features

- **📄 Multi-format Upload** — Drag & drop PDF, TXT, and DOCX files (up to 50MB)
- **🔍 RAG Pipeline** — Intelligent chunking, embedding, and retrieval via FAISS
- **💬 Streaming Chat** — Real-time, word-by-word responses via Server-Sent Events
- **📌 Source Citations** — Every answer shows which document and page it came from
- **⚙️ Configurable** — Adjust model, chunk size, top-K, and temperature from the UI
- **🔒 Privacy-first** — API keys stored in session only, never persisted
- **🐳 Docker Ready** — One command to run the full stack
- **📱 Responsive** — Works on desktop and mobile

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                 React Frontend (:3000)                  │
│  ┌──────────┐  ┌───────────────┐  ┌──────────────────┐  │
│  │ Document  │  │    Chat       │  │    Settings      │  │
│  │ Sidebar   │  │  Interface    │  │    Panel         │  │
│  └─────┬────┘  └───────┬───────┘  └────────┬─────────┘  │
└────────┼────────────────┼──────────────────┼────────────┘
         │   REST + SSE   │                  │
         ▼                ▼                  ▼
┌─────────────────────────────────────────────────────────┐
│               FastAPI Backend (:8000)                    │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  Document     │  │    RAG       │  │  Embeddings   │  │
│  │  Processor    │──│  Pipeline    │──│  Manager      │  │
│  │  (LangChain)  │  │  (FAISS)    │  │  (Ada-002)    │  │
│  └──────────────┘  └──────┬───────┘  └───────────────┘  │
│                           │                             │
└───────────────────────────┼─────────────────────────────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │ /uploads │  │  FAISS   │  │ OpenAI   │
        │ (files)  │  │  Index   │  │ API      │
        └──────────┘  │(in-mem)  │  │(GPT-4o + │
                      └──────────┘  │ Ada-002) │
                                    └──────────┘
```

---

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
# 1. Clone the repo
git clone https://github.com/mohamednoorulnaseem/RAG-Powered-Domain-Expert-System.git
cd RAG-Powered-Domain-Expert-System

# 2. (Optional) Set your API key in .env
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY — or set it later via the UI

# 3. Start both services
docker-compose up --build

# Frontend → http://localhost:3000
# Backend  → http://localhost:8000
```

### Option 2: Run Locally

**Backend:**
```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# (Optional) Set API key
set OPENAI_API_KEY=sk-your-key  # Windows
# export OPENAI_API_KEY=sk-your-key  # macOS/Linux

# Start the server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend:**
```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

Open **http://localhost:3000** in your browser.

---

## 📖 How to Use

1. **Set your API Key** — Click the ⚙️ settings icon (top right) and paste your OpenAI API key
2. **Upload Documents** — Drag & drop PDF, TXT, or DOCX files into the left sidebar
3. **Ask Questions** — Type any question in the chat box and press Enter
4. **View Sources** — Expand the citations below each answer to see exactly where the information came from
5. **Adjust Settings** — Tweak the model, retrieval parameters, and temperature to fine-tune responses

---

## 🔌 API Endpoints

| Method   | Endpoint              | Description                      |
|----------|-----------------------|----------------------------------|
| `GET`    | `/health`             | Health check                     |
| `POST`   | `/upload`             | Upload & process a document      |
| `GET`    | `/documents`          | List all uploaded documents      |
| `DELETE` | `/documents/{id}`     | Delete a document                |
| `POST`   | `/chat`               | Send message (non-streaming)     |
| `POST`   | `/chat/stream`        | Send message (SSE streaming)     |
| `GET`    | `/chat/history`       | Get conversation history         |
| `DELETE` | `/chat/history`       | Clear conversation history       |

---

## 🛠️ Tech Stack

| Layer          | Technology                         |
|----------------|------------------------------------|
| Frontend       | React 19, Tailwind CSS v4, Vite    |
| Backend        | Python 3.11, FastAPI               |
| LLM            | OpenAI GPT-4o / GPT-4o-mini       |
| Embeddings     | OpenAI text-embedding-ada-002      |
| Vector Store   | FAISS (in-memory)                  |
| Doc Processing | LangChain (PyPDF, docx2txt)        |
| Streaming      | Server-Sent Events (SSE)           |
| Containers     | Docker + docker-compose            |

---

## 📁 Project Structure

```
RAG-Powered-Domain-Expert-System/
├── backend/
│   ├── main.py                 # FastAPI application & endpoints
│   ├── rag_pipeline.py         # Core RAG pipeline (FAISS + LLM)
│   ├── document_processor.py   # Document loading & chunking
│   ├── embeddings.py           # OpenAI embeddings manager
│   ├── requirements.txt        # Python dependencies
│   └── uploads/                # Uploaded document storage
├── frontend/
│   ├── src/
│   │   ├── App.jsx             # Root component (3-panel layout)
│   │   ├── main.jsx            # React entry point
│   │   ├── index.css           # Global styles & design system
│   │   └── components/
│   │       ├── ChatInterface.jsx     # Chat messages & input
│   │       ├── DocumentSidebar.jsx   # Upload & document list
│   │       ├── MessageBubble.jsx     # Individual message rendering
│   │       └── SettingsPanel.jsx     # Configuration controls
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── Dockerfile.backend
├── Dockerfile.frontend
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---

## ⚙️ Environment Variables

| Variable         | Default | Description                              |
|------------------|---------|------------------------------------------|
| `OPENAI_API_KEY` | —       | OpenAI API key (or set via UI)           |
| `MAX_FILE_SIZE_MB` | `50`  | Maximum upload file size in MB           |
| `CHUNK_SIZE`     | `1000`  | Default characters per text chunk        |
| `CHUNK_OVERLAP`  | `200`   | Overlap between consecutive chunks       |

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
