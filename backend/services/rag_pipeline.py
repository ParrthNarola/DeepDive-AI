"""RAG Pipeline — 100% HuggingFace Inference API edition.

Embeddings : sentence-transformers/all-MiniLM-L6-v2 via HF Inference API
             (no PyTorch / no sentence-transformers package needed — API only)
LLM        : Qwen/Qwen2.5-72B-Instruct via HF free Serverless Inference API
Vector DB  : ChromaDB (local persistent)
"""

import asyncio
from typing import List

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.schema import Document
from langchain.embeddings.base import Embeddings
from huggingface_hub import InferenceClient
from pypdf import PdfReader

from config import settings
from ws.manager import manager


# ── Text splitter ─────────────────────────────────────────────
splitter = RecursiveCharacterTextSplitter(
    chunk_size=settings.CHUNK_SIZE,
    chunk_overlap=settings.CHUNK_OVERLAP,
    length_function=len,
    separators=["\n\n", "\n", ". ", " ", ""],
)


# ── HF Inference API Embeddings (no PyTorch required) ─────────
class HFAPIEmbeddings(Embeddings):
    """LangChain-compatible embeddings via HF feature-extraction API.

    Uses the same model (all-MiniLM-L6-v2) as before but calls the
    HF Serverless Inference API instead of running PyTorch locally.
    This removes the 800MB torch dependency — perfect for deployment.
    """

    def __init__(self, model: str, token: str):
        self._client = InferenceClient(token=token)
        self._model = model

    def _embed(self, texts: List[str]) -> List[List[float]]:
        results = []
        for text in texts:
            vec = self._client.feature_extraction(text, model=self._model)
            # feature_extraction returns numpy array or list — normalise to list[float]
            if hasattr(vec, "tolist"):
                vec = vec.tolist()
            # Some models return [[...]] (batched) — unwrap one level if needed
            if isinstance(vec[0], list):
                vec = vec[0]
            results.append(vec)
        return results

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._embed(texts)

    def embed_query(self, text: str) -> List[float]:
        return self._embed([text])[0]


# ── Lazy singletons ───────────────────────────────────────────
_embeddings: HFAPIEmbeddings | None = None
_hf_client: InferenceClient | None = None


def get_embeddings() -> HFAPIEmbeddings:
    global _embeddings
    if _embeddings is None:
        _embeddings = HFAPIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            token=settings.HUGGINGFACE_API_TOKEN,
        )
    return _embeddings


def get_hf_client() -> InferenceClient:
    global _hf_client
    if _hf_client is None:
        _hf_client = InferenceClient(
            model=settings.CHAT_MODEL,
            token=settings.HUGGINGFACE_API_TOKEN,
        )
    return _hf_client


# ── System prompts ────────────────────────────────────────────
RESEARCHER_SYSTEM = (
    "You are a Senior Research Assistant. Answer questions based ONLY on the "
    "provided context chunks. If the answer is not in the context, clearly say "
    "you do not have enough information. Always cite the page number (e.g. "
    "[Page 3]) where you found the information. Be concise and precise."
)

CONDENSE_SYSTEM = (
    "Given the conversation history and a follow-up question, rephrase the "
    "follow-up question as a complete standalone question. Return only the "
    "rephrased question, nothing else."
)


# ── PDF helpers ───────────────────────────────────────────────
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


# ── Embed & store ─────────────────────────────────────────────
async def embed_and_store(chunks: List[Document], doc_id: str) -> Chroma:
    """Embed chunks via HF API and persist to ChromaDB."""
    total = len(chunks)
    batch_size = 5   # smaller batches — API calls, not local
    emb = get_embeddings()

    vectorstore = Chroma(
        collection_name=f"doc_{doc_id}",
        embedding_function=emb,
        persist_directory=str(settings.CHROMA_DIR),
    )

    for i in range(0, total, batch_size):
        batch = chunks[i: i + batch_size]
        # Run synchronous HF API calls in thread pool
        await asyncio.to_thread(vectorstore.add_documents, batch)
        progress = min(i + batch_size, total)
        await manager.broadcast({
            "type": "pipeline_event",
            "event": "embedding_progress",
            "message": f"⚡ Embedding chunks {progress}/{total}",
            "current": progress,
            "total": total,
            "percentage": round(progress / total * 100),
        })

    return vectorstore


def get_vectorstore(doc_id: str) -> Chroma:
    return Chroma(
        collection_name=f"doc_{doc_id}",
        embedding_function=get_embeddings(),
        persist_directory=str(settings.CHROMA_DIR),
    )


# ── LLM helpers ───────────────────────────────────────────────
def _chat(messages: list, max_tokens: int = 256) -> str:
    """Synchronous HF chat call — run via asyncio.to_thread."""
    client = get_hf_client()
    resp = client.chat_completion(messages=messages, max_tokens=max_tokens, temperature=0.2)
    return resp.choices[0].message.content


async def _chat_streaming(messages: list) -> str:
    """Stream tokens from HF API and broadcast each via WebSocket."""
    client = get_hf_client()
    loop = asyncio.get_running_loop()

    def _stream() -> str:
        full = ""
        for chunk in client.chat_completion(
            messages=messages, max_tokens=1024, temperature=0.2, stream=True
        ):
            if not chunk.choices:
                continue
            token = chunk.choices[0].delta.content or ""
            full += token
            loop.call_soon_threadsafe(
                lambda t=token: asyncio.ensure_future(
                    manager.broadcast({"type": "llm_token", "token": t})
                )
            )
        return full

    return await asyncio.to_thread(_stream)


# ── Full RAG query ────────────────────────────────────────────
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

    # Retrieve (embedding API call runs in thread)
    await manager.broadcast({
        "type": "pipeline_event",
        "event": "retriever_start",
        "message": f'🔍 Searching: "{standalone[:80]}…"',
    })

    vs = get_vectorstore(doc_id)
    docs = await asyncio.to_thread(vs.similarity_search, standalone, k=settings.RETRIEVAL_K)

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
        "message": "🧠 Qwen is generating a response…",
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
