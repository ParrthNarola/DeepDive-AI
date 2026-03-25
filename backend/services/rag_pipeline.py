"""RAG Pipeline — HuggingFace Inference API + Qdrant Cloud edition.

Embeddings : sentence-transformers/all-MiniLM-L6-v2 via HF Inference API
             (no PyTorch / no sentence-transformers package needed — API only)
LLM        : mistralai/Mistral-7B-Instruct-v0.3 via HF free Serverless Inference API
Vector DB  : Qdrant Cloud (free hosted, persistent across restarts)
"""

import asyncio
import uuid
from typing import List

import httpx
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from pypdf import PdfReader

from config import settings
from ws.manager import manager


# ── Qdrant collection names ────────────────────────────────────
DOCS_REGISTRY = "__docs_registry__"


# ── Text splitter ──────────────────────────────────────────────
splitter = RecursiveCharacterTextSplitter(
    chunk_size=settings.CHUNK_SIZE,
    chunk_overlap=settings.CHUNK_OVERLAP,
    length_function=len,
    separators=["\n\n", "\n", ". ", " ", ""],
)


# ── HF Inference API Embeddings (no PyTorch required) ──────────
class HFAPIEmbeddings(Embeddings):
    """LangChain-compatible embeddings via HF feature-extraction API."""

    def __init__(self, model: str, token: str):
        self._model = model
        self._token = token
        # HF moved to router.huggingface.co — old api-inference.huggingface.co returns 410 Gone
        self._url = f"https://router.huggingface.co/hf-inference/models/{model}/pipeline/feature-extraction"
        self._headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def _embed(self, texts: List[str]) -> List[List[float]]:
        import httpx as _httpx
        resp = _httpx.post(
            self._url,
            headers=self._headers,
            json={"inputs": texts, "options": {"wait_for_model": True}},
            timeout=60,
        )
        resp.raise_for_status()
        result = resp.json()
        # Response shape: [[vec], [vec], ...] or [vec] for single input
        if isinstance(result[0][0], list):
            result = [r[0] for r in result]
        return result

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._embed(texts)

    def embed_query(self, text: str) -> List[float]:
        return self._embed([text])[0]


# ── Lazy singletons ────────────────────────────────────────────
_embeddings: HFAPIEmbeddings | None = None
# In-memory fallback store: collection_name → list of {id, vector, payload}
_memory_store: dict = {}


def get_embeddings() -> HFAPIEmbeddings:
    global _embeddings
    if _embeddings is None:
        _embeddings = HFAPIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            token=settings.HUGGINGFACE_API_TOKEN,
        )
    return _embeddings


# ── HF Classic Inference API helpers ───────────────────────────
# Uses api-inference.huggingface.co directly — bypasses router.huggingface.co
# which only serves paid providers for Mistral/Qwen/Llama models.
_HF_INFERENCE_BASE = "https://api-inference.huggingface.co"


def _hf_headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.HUGGINGFACE_API_TOKEN}",
        "Content-Type": "application/json",
        "x-use-cache": "0",
    }


# ── Qdrant REST helpers ────────────────────────────────────────
# Uses httpx directly — avoids qdrant-client which requires pydantic v2.

def _qdrant_headers() -> dict:
    h = {"Content-Type": "application/json"}
    if settings.QDRANT_API_KEY:
        h["api-key"] = settings.QDRANT_API_KEY
    return h


def _qdrant_url(path: str) -> str:
    base = settings.QDRANT_URL.rstrip("/")
    return f"{base}{path}"


def _collection_exists(name: str) -> bool:
    if not settings.QDRANT_URL:
        return name in _memory_store
    try:
        r = httpx.get(_qdrant_url(f"/collections/{name}"), headers=_qdrant_headers(), timeout=10)
        return r.status_code == 200
    except Exception:
        return False


def _create_collection(name: str, vector_size: int) -> None:
    if not settings.QDRANT_URL:
        _memory_store[name] = []
        return
    httpx.put(
        _qdrant_url(f"/collections/{name}"),
        headers=_qdrant_headers(),
        json={"vectors": {"size": vector_size, "distance": "Cosine"}},
        timeout=15,
    ).raise_for_status()


def _delete_collection(name: str) -> None:
    if not settings.QDRANT_URL:
        _memory_store.pop(name, None)
        return
    httpx.delete(_qdrant_url(f"/collections/{name}"), headers=_qdrant_headers(), timeout=10)


def _upsert_points(collection: str, points: list) -> None:
    """points: list of {id, vector, payload}"""
    if not settings.QDRANT_URL:
        _memory_store.setdefault(collection, []).extend(points)
        return
    httpx.put(
        _qdrant_url(f"/collections/{collection}/points"),
        headers=_qdrant_headers(),
        json={"points": points},
        timeout=30,
    ).raise_for_status()


def _search_points(collection: str, vector: list, limit: int) -> list:
    if not settings.QDRANT_URL:
        # Cosine similarity for in-memory fallback
        import math
        def cosine(a, b):
            dot = sum(x * y for x, y in zip(a, b))
            na = math.sqrt(sum(x * x for x in a))
            nb = math.sqrt(sum(x * x for x in b))
            return dot / (na * nb) if na and nb else 0
        pts = _memory_store.get(collection, [])
        scored = sorted(pts, key=lambda p: cosine(p["vector"], vector), reverse=True)
        return [{"payload": p["payload"], "score": cosine(p["vector"], vector)} for p in scored[:limit]]
    r = httpx.post(
        _qdrant_url(f"/collections/{collection}/points/search"),
        headers=_qdrant_headers(),
        json={"vector": vector, "limit": limit, "with_payload": True},
        timeout=15,
    )
    r.raise_for_status()
    return r.json().get("result", [])


def _scroll_points(collection: str, limit: int = 200) -> list:
    if not settings.QDRANT_URL:
        return _memory_store.get(collection, [])
    r = httpx.post(
        _qdrant_url(f"/collections/{collection}/points/scroll"),
        headers=_qdrant_headers(),
        json={"limit": limit, "with_payload": True},
        timeout=15,
    )
    r.raise_for_status()
    return r.json().get("result", {}).get("points", [])


def _count_points(collection: str) -> int:
    if not settings.QDRANT_URL:
        return len(_memory_store.get(collection, []))
    r = httpx.post(
        _qdrant_url(f"/collections/{collection}/points/count"),
        headers=_qdrant_headers(),
        json={},
        timeout=10,
    )
    if r.status_code != 200:
        return 0
    return r.json().get("result", {}).get("count", 0)


# ── System prompts ─────────────────────────────────────────────
RESEARCHER_SYSTEM = (
    "You are a Senior Research Assistant. Answer questions based ONLY on the "
    "provided context chunks. If the answer is not in the context, clearly say "
    "you do not have enough information.\n\n"
    "Format your responses using Markdown:\n"
    "- Use **bold** for key terms and important points\n"
    "- Use bullet lists or numbered lists where appropriate\n"
    "- Use headings (### ) to organise longer answers into sections\n"
    "- Use `code` formatting for technical terms, identifiers, or values\n"
    "- Always cite the page number (e.g. **[Page 3]**) inline where you found the information\n"
    "Be concise, structured, and precise."
)

CONDENSE_SYSTEM = (
    "Given the conversation history and a follow-up question, rephrase the "
    "follow-up question as a complete standalone question. Return only the "
    "rephrased question, nothing else."
)


# ── PDF helpers ────────────────────────────────────────────────
def extract_text_from_pdf(filepath) -> List[Document]:
    reader = PdfReader(str(filepath))
    docs: List[Document] = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            docs.append(
                Document(
                    page_content=text,
                    metadata={"page": i + 1, "source": str(filepath)},
                )
            )
    return docs


def chunk_documents(docs: List[Document]) -> List[Document]:
    chunks: List[Document] = []
    for doc in docs:
        sub = splitter.split_documents([doc])
        for j, chunk in enumerate(sub):
            chunk.metadata["chunk_index"] = j
        chunks.extend(sub)
    return chunks


# ── Embed & store ──────────────────────────────────────────────
async def embed_and_store(chunks: List[Document], doc_id: str) -> None:
    """Embed chunks via HF API and persist to Qdrant Cloud."""
    total = len(chunks)
    batch_size = 5
    emb = get_embeddings()
    collection_name = f"doc_{doc_id}"

    # Recreate collection so re-uploading the same doc starts fresh
    if _collection_exists(collection_name):
        await asyncio.to_thread(_delete_collection, collection_name)
    await asyncio.to_thread(_create_collection, collection_name, settings.EMBEDDING_DIM)

    for i in range(0, total, batch_size):
        batch = chunks[i: i + batch_size]
        texts = [c.page_content for c in batch]

        vectors = await asyncio.to_thread(emb.embed_documents, texts)

        points = [
            {
                "id": str(uuid.uuid4()),
                "vector": vec,
                "payload": {"text": chunk.page_content, **chunk.metadata},
            }
            for chunk, vec in zip(batch, vectors)
        ]
        await asyncio.to_thread(_upsert_points, collection_name, points)

        progress = min(i + batch_size, total)
        await manager.broadcast({
            "type": "pipeline_event",
            "event": "embedding_progress",
            "message": f"⚡ Embedding chunks {progress}/{total}",
            "current": progress,
            "total": total,
            "percentage": round(progress / total * 100),
        })


# ── Similarity search ──────────────────────────────────────────
async def search_similar(query: str, doc_id: str, k: int) -> List[Document]:
    """Embed query and retrieve top-k similar chunks from Qdrant."""
    query_vec = await asyncio.to_thread(get_embeddings().embed_query, query)
    results = await asyncio.to_thread(_search_points, f"doc_{doc_id}", query_vec, k)
    return [
        Document(
            page_content=r["payload"]["text"],
            metadata={key: val for key, val in r["payload"].items() if key != "text"},
        )
        for r in results
    ]


# ── Document registry (persisted in Qdrant) ────────────────────
def save_doc_meta(doc_id: str, filename: str, status: str) -> None:
    """Upsert document metadata into the Qdrant registry collection."""
    try:
        if not _collection_exists(DOCS_REGISTRY):
            # Registry uses a 1-dim dummy vector — we only need payload storage
            _create_collection(DOCS_REGISTRY, 1)
        _upsert_points(DOCS_REGISTRY, [{
            "id": str(uuid.UUID(int=int(doc_id, 16))),  # deterministic UUID from doc_id
            "vector": [0.0],
            "payload": {"doc_id": doc_id, "filename": filename, "status": status},
        }])
    except Exception:
        pass  # Non-fatal: in-memory registry still works for current session


def _delete_doc_meta(doc_id: str) -> None:
    """Remove a document entry from the Qdrant registry."""
    try:
        if not _collection_exists(DOCS_REGISTRY):
            return
        point_id = str(uuid.UUID(int=int(doc_id, 16)))
        if settings.QDRANT_URL:
            httpx.post(
                _qdrant_url(f"/collections/{DOCS_REGISTRY}/points/delete"),
                headers=_qdrant_headers(),
                json={"points": [point_id]},
                timeout=10,
            )
        else:
            _memory_store[DOCS_REGISTRY] = [
                p for p in _memory_store.get(DOCS_REGISTRY, [])
                if p.get("payload", {}).get("doc_id") != doc_id
            ]
    except Exception:
        pass


def load_all_docs() -> List[dict]:
    """Load all document metadata from the Qdrant registry."""
    try:
        if not _collection_exists(DOCS_REGISTRY):
            return []
        points = _scroll_points(DOCS_REGISTRY)
        return [p["payload"] for p in points]
    except Exception:
        return []


# ── Prompt formatter ──────────────────────────────────────────
def _format_prompt(messages: list) -> str:
    """Format chat messages into Mistral [INST] prompt for text_generation API."""
    parts = []
    system_content = ""
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        if role == "system":
            system_content = content
        elif role == "user":
            # Prepend system prompt into the first user turn
            if system_content:
                content = f"{system_content}\n\n{content}"
                system_content = ""
            parts.append(f"[INST] {content} [/INST]")
        elif role == "assistant":
            parts.append(f"{content}</s>")
    return "".join(parts)


# ── LLM helpers ───────────────────────────────────────────────
def _chat(messages: list, max_tokens: int = 256) -> str:
    """Call HF classic inference API directly — bypasses the paid router."""
    prompt = _format_prompt(messages)
    resp = httpx.post(
        f"{_HF_INFERENCE_BASE}/models/{settings.CHAT_MODEL}",
        headers=_hf_headers(),
        json={
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": max_tokens,
                "temperature": 0.2,
                "return_full_text": False,
                "do_sample": True,
            },
        },
        timeout=60,
    )
    resp.raise_for_status()
    result = resp.json()
    if isinstance(result, list):
        return result[0].get("generated_text", "")
    return str(result)


async def _chat_streaming(messages: list) -> str:
    """Stream tokens from HF classic inference API via SSE and broadcast via WebSocket."""
    import json as _json

    prompt = _format_prompt(messages)
    full = ""

    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream(
            "POST",
            f"{_HF_INFERENCE_BASE}/models/{settings.CHAT_MODEL}",
            headers=_hf_headers(),
            json={
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 1024,
                    "temperature": 0.2,
                    "return_full_text": False,
                    "do_sample": True,
                },
                "stream": True,
            },
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data_str = line[5:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    data = _json.loads(data_str)
                    token = data.get("token", {}).get("text", "")
                    if token:
                        full += token
                        await manager.broadcast({"type": "llm_token", "token": token})
                except _json.JSONDecodeError:
                    pass

    # Fallback: if SSE gave nothing, do a plain blocking call
    if not full:
        full = await asyncio.to_thread(_chat, messages, 1024)

    return full


# ── Full RAG query ─────────────────────────────────────────────
async def query_rag(query: str, doc_id: str, history: list | None = None) -> str:
    """Condense → retrieve → answer with citations."""

    chat_history = []
    if history:
        for msg in history:
            role = "user" if msg["role"] == "user" else "assistant"
            chat_history.append({"role": role, "content": msg["content"]})

    # Condense follow-up into standalone question
    standalone = query
    if chat_history:
        condense_msgs = [
            {"role": "system", "content": CONDENSE_SYSTEM},
            *chat_history,
            {"role": "user", "content": f"Follow-up: {query}\nStandalone question:"},
        ]
        standalone = await asyncio.to_thread(_chat, condense_msgs, 128)
        standalone = standalone.strip()

    # Retrieve
    await manager.broadcast({
        "type": "pipeline_event",
        "event": "retriever_start",
        "message": f'🔍 Searching: "{standalone[:80]}…"',
    })

    docs = await search_similar(standalone, doc_id, settings.RETRIEVAL_K)

    await manager.broadcast({
        "type": "pipeline_event",
        "event": "retriever_end",
        "message": f"📄 Retrieved {len(docs)} chunks",
        "chunks": [
            {
                "index": i + 1,
                "page": d.metadata.get("page", "?"),
                "snippet": d.page_content[:120].replace("\n", " "),
            }
            for i, d in enumerate(docs)
        ],
    })

    # Build context
    context = "\n\n---\n\n".join(
        f"[Page {d.metadata.get('page', '?')}]\n{d.page_content}" for d in docs
    )

    # Generate answer with streaming
    await manager.broadcast({
        "type": "pipeline_event",
        "event": "llm_start",
        "message": "🧠 Mistral is generating a response…",
    })

    answer_msgs = [
        {"role": "system", "content": f"{RESEARCHER_SYSTEM}\n\nContext:\n{context}"},
        *chat_history,
        {"role": "user", "content": standalone},
    ]
    answer = await _chat_streaming(answer_msgs)

    await manager.broadcast({
        "type": "pipeline_event",
        "event": "llm_end",
        "message": "✅ Response complete",
    })

    return answer
