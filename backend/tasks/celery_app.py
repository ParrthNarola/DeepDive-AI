"""Celery application instance."""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# ── CRITICAL: add backend/ to sys.path FIRST ─────────────────
# Celery forks worker processes that lose the parent's sys.path.
# Without this, imports like 'from services.x import y' fail in workers.
_backend_dir = str(Path(__file__).resolve().parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

# Load .env so worker process has HUGGINGFACE_API_TOKEN
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

from celery import Celery
from config import settings

celery_app = Celery(
    "deepdive",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["tasks.process_document"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    # Use solo pool (no forking) — PyTorch/sentence-transformers segfault when
    # forked via prefork on macOS. Solo runs tasks in the main process.
    worker_pool="solo",
    broker_connection_retry_on_startup=True,
)
