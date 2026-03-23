"""LangChain Async Callback Handler — broadcasts RAG pipeline events in real time."""

import asyncio
from typing import Any, Optional
from uuid import UUID

from langchain.callbacks.base import AsyncCallbackHandler
from ws.manager import manager


class PipelineCallbackHandler(AsyncCallbackHandler):
    """Fires WebSocket events at key points in the LangChain pipeline."""

    async def on_retriever_start(self, serialized: dict[str, Any], query: str, **kwargs):
        await manager.broadcast({
            "type": "pipeline_event",
            "event": "retriever_start",
            "message": f"🔍 Searching for relevant chunks: \"{query[:80]}…\"",
        })

    async def on_retriever_end(self, documents, **kwargs):
        chunk_summaries = []
        for i, doc in enumerate(documents):
            page = doc.metadata.get("page", "?")
            snippet = doc.page_content[:120].replace("\n", " ")
            chunk_summaries.append({"index": i + 1, "page": page, "snippet": snippet})

        await manager.broadcast({
            "type": "pipeline_event",
            "event": "retriever_end",
            "message": f"📄 Retrieved {len(documents)} chunks",
            "chunks": chunk_summaries,
        })

    async def on_llm_start(self, serialized: dict[str, Any], prompts: list[str], **kwargs):
        await manager.broadcast({
            "type": "pipeline_event",
            "event": "llm_start",
            "message": "🧠 LLM is generating a response…",
        })

    async def on_llm_new_token(self, token: str, **kwargs):
        await manager.broadcast({
            "type": "llm_token",
            "token": token,
        })

    async def on_llm_end(self, response, **kwargs):
        await manager.broadcast({
            "type": "pipeline_event",
            "event": "llm_end",
            "message": "✅ Response complete",
        })

    async def on_llm_error(self, error: BaseException, **kwargs):
        await manager.broadcast({
            "type": "pipeline_event",
            "event": "llm_error",
            "message": f"❌ LLM error: {str(error)[:200]}",
        })
