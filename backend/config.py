"""Centralised application settings."""

from pydantic import BaseSettings
from pathlib import Path
import os


class Settings(BaseSettings):
    # ── API Keys ──────────────────────────────────────────────
    HUGGINGFACE_API_TOKEN: str = ""

    # ── Redis / Celery ────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Storage ───────────────────────────────────────────────
    BASE_DIR: Path = Path(__file__).resolve().parent
    UPLOAD_DIR: Path = Path(os.getenv("UPLOAD_DIR", BASE_DIR / "uploads"))
    CHROMA_DIR: Path = Path(os.getenv("CHROMA_DIR", BASE_DIR / "chroma_data"))

    # ── Chunking ──────────────────────────────────────────────
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200

    # ── Models ────────────────────────────────────────────────
    # Embedding: runs 100% locally via sentence-transformers (no API key needed)
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    # Chat LLM: HuggingFace free Serverless Inference API
    CHAT_MODEL: str = "Qwen/Qwen2.5-72B-Instruct"

    # ── RAG ───────────────────────────────────────────────────
    RETRIEVAL_K: int = 5

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# Ensure directories exist
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.CHROMA_DIR.mkdir(parents=True, exist_ok=True)
