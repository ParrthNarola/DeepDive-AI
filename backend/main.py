"""DeepDive AI — FastAPI application entry point."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from ws.manager import manager
from routers import upload, chat, documents
from services.resource_monitor import poll_resources

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     """Application lifespan — starts background tasks on startup."""
#     task = asyncio.create_task(poll_resources())
#     yield
#     task.cancel()
#     try:
#         await task
#     except asyncio.CancelledError:
#         pass


app = FastAPI(
    title="DeepDive AI",
    description="Real-Time Research Assistant — RAG pipeline with live dashboard",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS (allow Next.js dev server) ─────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── REST routers ────────────────────────────────────────────
app.include_router(upload.router)
app.include_router(chat.router)
app.include_router(documents.router)


# ── WebSocket endpoint ──────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; clients can send pings
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)


# ── Health check ────────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "DeepDive AI"}
