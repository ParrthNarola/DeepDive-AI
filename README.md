# DeepDive AI 🔬

A real-time AI research assistant. Upload PDFs, watch the RAG pipeline process them live, and chat with your documents using Qwen2.5-72B.

![DeepDive Dashboard](https://img.shields.io/badge/Stack-FastAPI%20%7C%20Next.js%20%7C%20ChromaDB%20%7C%20HuggingFace-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## ✨ Features

- 📁 **PDF Upload** — drag-and-drop with real-time progress
- ⚡ **Live Pipeline Feed** — watch extraction → chunking → embedding in real time
- 🧠 **RAG Chat** — Qwen2.5-72B answers questions with page citations
- 📊 **Resource Monitor** — live CPU & RAM sparklines
- 🔌 **WebSocket** — all updates pushed instantly, no polling

## 🏗️ Architecture

```
┌─────────────────┐     WebSocket      ┌──────────────────┐
│   Next.js UI    │◄──────────────────►│  FastAPI Backend  │
│   (Vercel)      │     REST API       │  (Render)         │
└─────────────────┘                    └────────┬─────────┘
                                                │ Celery task
                                       ┌────────▼─────────┐
                                       │  HuggingFace API  │
                                       │  • Embeddings     │
                                       │  • Qwen2.5-72B    │
                                       └──────────────────┘
                                       ┌──────────────────┐
                                       │    ChromaDB       │
                                       │  (Render disk)    │
                                       └──────────────────┘
```

## 🚀 Quick Start (Local)

### Prerequisites
- Python 3.12+
- Node.js 18+
- Redis (`brew install redis`)
- Free HuggingFace account → [get API token](https://huggingface.co/settings/tokens)

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
# Edit .env and add your HUGGINGFACE_API_TOKEN

# Start Redis
brew services start redis

# Run backend
uvicorn main:app --reload

# Run Celery worker (new terminal)
celery -A tasks.celery_app worker --loglevel=info
```

### 3. Frontend
```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## 🌐 Free Deployment

### Step 1 — Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/deepdive-ai.git
git push -u origin main
```

### Step 2 — Deploy Backend on Render
1. Go to [render.com](https://render.com) → New → Blueprint
2. Connect your GitHub repo
3. Render reads `render.yaml` automatically and creates:
   - `deepdive-api` (FastAPI web service)
   - `deepdive-celery` (Celery worker)
   - `deepdive-redis` (managed Redis)
4. In the dashboard, set the `HUGGINGFACE_API_TOKEN` secret for both services

### Step 3 — Deploy Frontend on Vercel
1. Go to [vercel.com](https://vercel.com) → New Project
2. Import your GitHub repo
3. Set **Root Directory** to `frontend`
4. Add environment variable:
   - `NEXT_PUBLIC_API_URL` = `https://deepdive-api.onrender.com`
   - `NEXT_PUBLIC_WS_URL` = `wss://deepdive-api.onrender.com`
5. Deploy ✅

## ⚙️ Environment Variables

### Backend (`backend/.env`)
| Variable | Description |
|----------|-------------|
| `HUGGINGFACE_API_TOKEN` | HF API token (required) — [get one free](https://huggingface.co/settings/tokens) |
| `REDIS_URL` | Redis connection string (default: `redis://localhost:6379/0`) |

### Frontend
| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Backend URL (default: `http://localhost:8000`) |
| `NEXT_PUBLIC_WS_URL` | WebSocket URL (default: `ws://localhost:8000`) |

## 🤖 Models Used

| Task | Model | Where |
|------|-------|-------|
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` | HF Inference API |
| Chat LLM | `Qwen/Qwen2.5-72B-Instruct` | HF Inference API |
| Vector DB | ChromaDB | Local disk |

## 📁 Project Structure

```
deepdive-ai/
├── backend/
│   ├── main.py                 # FastAPI app
│   ├── config.py               # Settings
│   ├── routers/
│   │   ├── upload.py           # PDF upload endpoint
│   │   ├── chat.py             # RAG chat endpoint
│   │   └── documents.py        # Document list endpoint
│   ├── services/
│   │   ├── rag_pipeline.py     # Core RAG logic
│   │   ├── callbacks.py        # LangChain callbacks
│   │   └── resource_monitor.py # CPU/RAM monitoring
│   ├── tasks/
│   │   ├── celery_app.py       # Celery config
│   │   └── process_document.py # Background task
│   ├── ws/
│   │   └── manager.py          # WebSocket manager
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/                # Next.js pages
│   │   ├── components/         # UI components
│   │   ├── hooks/              # useWebSocket
│   │   └── lib/api.ts          # API client
│   └── vercel.json
├── render.yaml                 # Render deployment config
├── .gitignore
└── README.md
```

## 📄 License

MIT — free to use and modify.
