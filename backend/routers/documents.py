"""Documents router — lists uploaded documents and their status."""

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["documents"])


@router.get("/documents")
async def list_documents():
    """Return all known documents and their processing status."""
    from routers.upload import documents
    return {"documents": list(documents.values())}
