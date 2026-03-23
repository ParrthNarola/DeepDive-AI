"""Celery task: process an uploaded document through the RAG pipeline."""

import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# ── Ensure backend/ is in sys.path BEFORE any local imports ──────────────────
# This must be the very first thing — both the main Celery process and every
# forked ForkPoolWorker need to resolve 'services', 'ws', 'config', etc.
_backend_dir = str(Path(__file__).resolve().parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

# Load .env so HUGGINGFACE_API_TOKEN is available in worker environment
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# ── Module-level imports (resolved in main process, inherited by workers) ─────
# DO NOT use lazy imports inside the task function — they fail in forked workers
# on macOS because the deferred import runs in the fork's context.
from tasks.celery_app import celery_app                                    # noqa: E402
from ws.manager import manager                                             # noqa: E402
from services.rag_pipeline import (                                        # noqa: E402
    extract_text_from_pdf,
    chunk_documents,
    embed_and_store,
)


async def _run_pipeline(file_path: str, doc_id: str) -> int:
    """Full async pipeline — embedding + ChromaDB storage."""

    async def emit(event: str, message: str, **extra):
        await manager.broadcast({
            "type": "pipeline_event",
            "event": event,
            "doc_id": doc_id,
            "message": message,
            **extra,
        })

    # Stage 1: Upload received
    await emit("upload_complete", "📥 Upload complete — starting processing…")

    # Stage 2: PDF text extraction
    await emit("extraction_start", "📖 Extracting text from PDF…")
    docs = extract_text_from_pdf(file_path)
    await emit("extraction_complete", f"📖 Extracted text from {len(docs)} pages")

    # Stage 3: Chunking
    await emit("chunking_start", "✂️ Splitting text into chunks…")
    chunks = chunk_documents(docs)
    await emit("chunking_complete", f"✂️ Created {len(chunks)} chunks",
               total_chunks=len(chunks))

    # Stage 4: Embed & store (local sentence-transformers, no API call)
    await emit("embedding_start", "⚡ Embedding chunks into vector store…")
    await embed_and_store(chunks, doc_id)

    await emit("processing_complete", "✅ Document processed and ready for chat!")
    return len(chunks)


@celery_app.task(bind=True, name="tasks.process_document")
def process_document(self, file_path: str, doc_id: str):
    """Entry point called by Celery. Runs the async pipeline in a fresh event loop."""
    try:
        n_chunks = asyncio.run(_run_pipeline(file_path, doc_id))
        return {"status": "success", "doc_id": doc_id, "chunks": n_chunks}
    except Exception as exc:
        try:
            asyncio.run(manager.broadcast({
                "type": "pipeline_event",
                "event": "processing_error",
                "doc_id": doc_id,
                "message": f"❌ Processing failed: {str(exc)[:300]}",
            }))
        except Exception:
            pass
        raise self.retry(exc=exc, countdown=10, max_retries=2)
