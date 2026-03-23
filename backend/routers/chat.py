"""Chat router — handles RAG queries against processed documents."""

import chromadb
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.rag_pipeline import query_rag
from config import settings

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    query: str
    document_id: str
    history: list[dict] | None = None


class ChatResponse(BaseModel):
    answer: str
    document_id: str


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Query the RAG pipeline for a processed document."""

    # ── Step 1: Verify data exists — no API call needed ──────
    try:
        client = chromadb.PersistentClient(path=str(settings.CHROMA_DIR))
        collection_name = f"doc_{request.document_id}"
        existing_names = [c.name for c in client.list_collections()]

        if collection_name not in existing_names:
            raise HTTPException(
                status_code=404,
                detail=f"Document '{request.document_id}' not found. Upload and process it first.",
            )

        col = client.get_collection(collection_name)
        if col.count() == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Document '{request.document_id}' is still processing. Please wait for the Activity Feed to show ✅.",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Storage check error: {str(e)}")

    # ── Step 2: Run RAG query ────────────────────────────────
    try:
        answer = await query_rag(
            query=request.query,
            doc_id=request.document_id,
            history=request.history,
        )
    except Exception as e:
        err = str(e)
        if "429" in err or "quota" in err.lower() or "ResourceExhausted" in err:
            raise HTTPException(
                status_code=429,
                detail=(
                    "Gemini API free-tier quota exceeded. "
                    "Wait ~1 minute and retry, or check your limits at https://ai.dev/rate-limit"
                ),
            )
        raise HTTPException(status_code=500, detail=f"LLM error: {err[:400]}")

    return ChatResponse(answer=answer, document_id=request.document_id)
