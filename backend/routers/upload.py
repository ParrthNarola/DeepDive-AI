"""Upload router — handles PDF file uploads and dispatches processing."""

import uuid
import shutil
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException
from config import settings
from ws.manager import manager

router = APIRouter(prefix="/api", tags=["upload"])

# In-memory document registry (swap for DB in production)
documents: dict[str, dict] = {}


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Accept a PDF upload, save it locally, and fire off the processing task."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    doc_id = uuid.uuid4().hex[:12]
    save_path = settings.UPLOAD_DIR / f"{doc_id}_{file.filename}"

    # Save file
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Register document
    documents[doc_id] = {
        "id": doc_id,
        "filename": file.filename,
        "path": str(save_path),
        "status": "processing",
    }

    # Broadcast upload event
    await manager.broadcast({
        "type": "pipeline_event",
        "event": "file_received",
        "doc_id": doc_id,
        "message": f"📁 File received: {file.filename}",
    })

    # Dispatch Celery task or fall back to inline processing
    try:
        from tasks.process_document import process_document
        process_document.delay(str(save_path), doc_id)
        # Status stays "processing" — the Celery task will broadcast
        # processing_complete when done, and DocumentList refreshes on that event.
    except Exception:
        # If Celery/Redis aren't available, process inline (dev fallback)
        import asyncio
        from services.rag_pipeline import extract_text_from_pdf, chunk_documents, embed_and_store

        await manager.broadcast({
            "type": "pipeline_event",
            "event": "fallback_processing",
            "doc_id": doc_id,
            "message": "⚠️ Celery unavailable — processing inline…",
        })

        try:
            docs = extract_text_from_pdf(str(save_path))
            chunks = chunk_documents(docs)
            await embed_and_store(chunks, doc_id)

            documents[doc_id]["status"] = "ready"  # Only set after success
            await manager.broadcast({
                "type": "pipeline_event",
                "event": "processing_complete",
                "doc_id": doc_id,
                "message": "✅ Document processed and ready for chat!",
            })
        except Exception as e:
            documents[doc_id]["status"] = "error"
            await manager.broadcast({
                "type": "pipeline_event",
                "event": "processing_error",
                "doc_id": doc_id,
                "message": f"❌ Processing failed: {str(e)[:200]}",
            })

    return {"doc_id": doc_id, "filename": file.filename, "status": "processing"}
