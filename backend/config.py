"""Centralised application settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
import os


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # ── API Keys ──────────────────────────────────────────────
    HUGGINGFACE_API_TOKEN: str = ""

    # ── Redis / Celery ────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Qdrant Cloud ──────────────────────────────────────────
    # Set these in Render dashboard (or .env for local dev)
    # Leave empty to fall back to in-memory mode (local dev only — data lost on restart)
    QDRANT_URL: str = ""
    QDRANT_API_KEY: str = ""
    # Dimension of sentence-transformers/all-MiniLM-L6-v2 embeddings
    EMBEDDING_DIM: int = 384

    # ── Storage ───────────────────────────────────────────────
    BASE_DIR: Path = Path(__file__).resolve().parent
    # PDFs are only needed during inline processing — /tmp is fine
    UPLOAD_DIR: Path = Path(os.getenv("UPLOAD_DIR", str(Path(__file__).resolve().parent / "uploads")))

    # ── Celery ────────────────────────────────────────────────
    USE_CELERY: bool = False

    # ── Chunking ──────────────────────────────────────────────
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200

    # ── Models ────────────────────────────────────────────────
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    CHAT_MODEL: str = "Qwen/Qwen2.5-72B-Instruct"

    # ── RAG ───────────────────────────────────────────────────
    RETRIEVAL_K: int = 5


settings = Settings()

# Ensure upload directory exists
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
