"""Documents router — lists and deletes uploaded documents."""

from fastapi import APIRouter, HTTPException

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
    # Normalise to always return "id" (frontend expects this key)
    return {
        "documents": [
            {"id": d["doc_id"], "filename": d["filename"], "status": d["status"]}
            for d in persisted.values()
        ]
    }


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document: removes vectors from Qdrant and the registry entry."""
    from services.rag_pipeline import _collection_exists, _delete_collection, _delete_doc_meta
    from routers.upload import documents as session_docs

    collection_name = f"doc_{doc_id}"

    # Remove vector collection from Qdrant
    if _collection_exists(collection_name):
        _delete_collection(collection_name)

    # Remove from registry
    _delete_doc_meta(doc_id)

    # Remove from in-memory session registry
    session_docs.pop(doc_id, None)

    return {"deleted": doc_id}
