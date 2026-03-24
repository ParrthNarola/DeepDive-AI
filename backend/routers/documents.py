"""Documents router — lists uploaded documents and their status."""

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["documents"])


@router.get("/documents")
async def list_documents():
    """Return all known documents. Loads from Qdrant so the list survives restarts."""
    from services.rag_pipeline import load_all_docs
    from routers.upload import documents as session_docs

    # Merge: Qdrant (persistent) + current session (has in-progress states)
    persisted = {d["doc_id"]: d for d in load_all_docs()}
    persisted.update({
        doc_id: {"doc_id": doc_id, "filename": d["filename"], "status": d["status"]}
        for doc_id, d in session_docs.items()
    })
    return {"documents": list(persisted.values())}
