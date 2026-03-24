"""Upload router — handles PDF file uploads and dispatches processing."""

import uuid
import shutil
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException
from config import settings
from ws.manager import manager

router = APIRouter(prefix="/api", tags=["upload"])

# In-memory registry for the current session (Qdrant is the persistent source of truth)
documents: dict[str, dict] = {}


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Accept a PDF upload, save to /tmp, and process it inline."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    doc_id = uuid.uuid4().hex[:12]
    save_path = settings.UPLOAD_DIR / f"{doc_id}_{file.filename}"

    # Save file to /tmp (only needed during processing)
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Register in memory + persist to Qdrant
    documents[doc_id] = {
        "id": doc_id,
        "filename": file.filename,
        "path": str(save_path),
        "status": "processing",
    }
    from services.rag_pipeline import save_doc_meta
    save_doc_meta(doc_id, file.filename, "processing")

    await manager.broadcast({
        "type": "pipeline_event",
        "event": "file_received",
        "doc_id": doc_id,
        "message": f"📁 File received: {file.filename}",
    })

    if settings.USE_CELERY:
        # Only use when shared external storage is configured so the worker
        # can access the same files as the web service.
        try:
            from tasks.process_document import process_document
            process_document.delay(str(save_path), doc_id)
        except Exception:
            await _process_inline(save_path, doc_id)
    else:
        await _process_inline(save_path, doc_id)

    return {"doc_id": doc_id, "filename": file.filename, "status": "processing"}


async def _process_inline(save_path: Path, doc_id: str) -> None:
    """Run the full RAG pipeline in-process and persist status to Qdrant."""
    from services.rag_pipeline import (
        extract_text_from_pdf, chunk_documents,
        embed_and_store, save_doc_meta,
    )

    try:
        docs = extract_text_from_pdf(str(save_path))
        chunks = chunk_documents(docs)
        await embed_and_store(chunks, doc_id)

        documents[doc_id]["status"] = "ready"
        save_doc_meta(doc_id, documents[doc_id]["filename"], "ready")

        await manager.broadcast({
            "type": "pipeline_event",
            "event": "processing_complete",
            "doc_id": doc_id,
            "message": "✅ Document processed and ready for chat!",
        })
    except Exception as e:
        documents[doc_id]["status"] = "error"
        save_doc_meta(doc_id, documents[doc_id]["filename"], "error")

        await manager.broadcast({
            "type": "pipeline_event",
            "event": "processing_error",
            "doc_id": doc_id,
            "message": f"❌ Processing failed: {str(e)[:200]}",
        })
    finally:
        # Clean up the temp file — vectors are now in Qdrant, file no longer needed
        try:
            save_path.unlink(missing_ok=True)
        except Exception:
            pass
