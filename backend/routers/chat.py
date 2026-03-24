"""Chat router — handles RAG queries against processed documents."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.rag_pipeline import query_rag, _collection_exists, _count_points

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

    # ── Verify document exists in Qdrant ─────────────────────
    try:
        collection_name = f"doc_{request.document_id}"

        if not _collection_exists(collection_name):
            raise HTTPException(
                status_code=404,
                detail=f"Document '{request.document_id}' not found. Upload and process it first.",
            )

        if _count_points(collection_name) == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Document '{request.document_id}' is still processing. Please wait for the Activity Feed to show ✅.",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Storage check error: {str(e)}")

    # ── Run RAG query ─────────────────────────────────────────
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
                    "HuggingFace API free-tier quota exceeded. "
                    "Wait ~1 minute and retry."
                ),
            )
        raise HTTPException(status_code=500, detail=f"LLM error: {err[:400]}")

    return ChatResponse(answer=answer, document_id=request.document_id)
