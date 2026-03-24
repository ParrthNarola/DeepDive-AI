# DeepDive AI 🔬

A real-time AI research assistant. Upload PDFs, watch the RAG pipeline process them live, and chat with your documents using Qwen2.5-72B.

![DeepDive Dashboard](https://img.shields.io/badge/Stack-FastAPI%20%7C%20Next.js%20%7C%20Qdrant%20%7C%20HuggingFace-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## ✨ Features

- 📁 **PDF Upload** — drag-and-drop with real-time progress
- ⚡ **Live Pipeline Feed** — watch extraction → chunking → embedding in real time
- 🧠 **RAG Chat** — Qwen2.5-72B answers questions with page citations
- 📊 **Resource Monitor** — live CPU & RAM sparklines
- 🔌 **WebSocket** — all updates pushed instantly, no polling
- ☁️ **Persistent Vectors** — Qdrant Cloud keeps embeddings across restarts

## 🏗️ Architecture

```
┌─────────────────┐     WebSocket      ┌──────────────────┐
│   Next.js UI    │◄──────────────────►│  FastAPI Backend  │
│   (Vercel)      │     REST API       │  (Render)         │
└─────────────────┘                    └────────┬─────────┘
                                                │
                                    ┌───────────┼───────────┐
                                    ▼           ▼           ▼
                             ┌──────────┐ ┌─────────┐ ┌──────────┐
                             │  Qdrant  │ │   HF    │ │   HF     │
                             │  Cloud   │ │Embeddings│ │  Qwen    │
                             │(vectors) │ │   API   │ │  LLM API │
                             └──────────┘ └─────────┘ └──────────┘
```

## 🚀 Quick Start (Local)

### Prerequisites
- Python 3.11+
- Node.js 18+
- Free [HuggingFace](https://huggingface.co/settings/tokens) account → API token
- Free [Qdrant Cloud](https://cloud.qdrant.io) account → cluster URL + API key

### 1. Clone
```bash
git clone https://github.com/YOUR_USERNAME/deepdive-ai.git
cd deepdive-ai
```

### 2. Backend
```bash
cd backend
pip install -r requirements.txt

# Create .env
cp .env.example .env
# Edit .env — add HUGGINGFACE_API_TOKEN, QDRANT_URL, QDRANT_API_KEY

uvicorn main:app --reload
```

### 3. Frontend
```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

> **Local dev note:** If you leave `QDRANT_URL` empty in `.env`, the app falls back to an in-memory Qdrant instance — data is lost on restart but everything works for testing.

## 🌐 Free Deployment

### Step 1 — Set up Qdrant Cloud (free, no credit card)
1. Go to [cloud.qdrant.io](https://cloud.qdrant.io) → Sign up
2. Create a new cluster → select **Free tier** → any region
3. Copy the **Cluster URL** and **API Key** from the cluster dashboard

### Step 2 — Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/deepdive-ai.git
git push -u origin main
```

### Step 3 — Deploy Backend on Render
1. Go to [render.com](https://render.com) → New → **Blueprint**
2. Connect your GitHub repo — Render reads `render.yaml` automatically
3. In the `deepdive-api` service → **Environment**, add these secrets:

| Key | Value |
|-----|-------|
| `HUGGINGFACE_API_TOKEN` | `hf_xxxx` |
| `QDRANT_URL` | `https://xxxx.cloud.qdrant.io:6333` |
| `QDRANT_API_KEY` | your Qdrant API key |
| `FRONTEND_URL` | `https://your-app.vercel.app` |

4. Deploy ✅

### Step 4 — Deploy Frontend on Vercel
1. Go to [vercel.com](https://vercel.com) → New Project
2. Import your GitHub repo → set **Root Directory** to `frontend`
3. Add environment variables:
   - `NEXT_PUBLIC_API_URL` = `https://deepdive-api.onrender.com`
   - `NEXT_PUBLIC_WS_URL` = `wss://deepdive-api.onrender.com`
4. Deploy ✅

## ⚙️ Environment Variables

### Backend (`backend/.env`)
| Variable | Required | Description |
|----------|----------|-------------|
| `HUGGINGFACE_API_TOKEN` | Yes | [Get free token](https://huggingface.co/settings/tokens) |
| `QDRANT_URL` | Yes (prod) | Qdrant Cloud cluster URL |
| `QDRANT_API_KEY` | Yes (prod) | Qdrant Cloud API key |
| `FRONTEND_URL` | Yes (prod) | Vercel frontend URL for CORS |
| `USE_CELERY` | No | `false` (default) — set `true` only with shared external storage |

### Frontend
| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Backend URL (default: `http://localhost:8000`) |
| `NEXT_PUBLIC_WS_URL` | WebSocket URL (default: `ws://localhost:8000`) |

## 🤖 Models & Services

| Component | Service | Free Tier |
|-----------|---------|-----------|
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` via HF Inference API | Yes |
| Chat LLM | `Qwen/Qwen2.5-72B-Instruct` via HF Inference API | Yes |
| Vector DB | [Qdrant Cloud](https://cloud.qdrant.io) | Yes — 1GB, never pauses |
| Backend hosting | [Render](https://render.com) | Yes — free web service |
| Frontend hosting | [Vercel](https://vercel.com) | Yes |

## 📁 Project Structure

```
deepdive-ai/
├── backend/
│   ├── main.py                 # FastAPI app + CORS + WebSocket
│   ├── config.py               # Settings (env vars via Pydantic)
│   ├── routers/
│   │   ├── upload.py           # POST /api/upload
│   │   ├── chat.py             # POST /api/chat
│   │   └── documents.py        # GET /api/documents
│   ├── services/
│   │   ├── rag_pipeline.py     # Core RAG: extract → chunk → embed → Qdrant
│   │   ├── callbacks.py        # LangChain callbacks
│   │   └── resource_monitor.py # CPU/RAM monitoring
│   ├── tasks/
│   │   ├── celery_app.py       # Celery config (optional, disabled on Render)
│   │   └── process_document.py # Background task (optional)
│   ├── ws/
│   │   └── manager.py          # WebSocket broadcast manager
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/                # Next.js app router
│   │   ├── components/         # UploadPanel, ChatPanel, DocumentList, etc.
│   │   ├── hooks/              # useWebSocket (auto-reconnect)
│   │   └── lib/api.ts          # Fetch wrappers
│   └── vercel.json
├── render.yaml                 # Render deployment config (single web service)
└── README.md
```

## 🔒 Version Lock Notice

The backend uses a carefully pinned dependency stack. **Do not upgrade these without upgrading all together:**

```
pydantic==1.10.13       ← v2 breaks langchain + config
langchain==0.0.350      ← requires pydantic v1
chromadb removed        ← replaced by qdrant-client
fastapi==0.95.2         ← v0.100+ dropped full pydantic v1 support
```

## 📄 License

MIT — free to use and modify.
