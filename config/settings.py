"""Load settings from env. Use .env or set TIER, INFERENCE_URL, etc."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

TIER_CHOICES = ("dev", "test", "demo")

# Project root (repo root where pyproject.toml lives). Relative INDEX_PATH/REPO_PATH are resolved from here.
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _str(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def _int(key: str, default: int = 0) -> int:
    raw = _str(key)
    return int(raw) if raw.isdigit() else default


def _path(key: str, default: str = "") -> Path:
    raw = _str(key) or default
    if not raw:
        return Path()
    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = (PROJECT_ROOT / p).resolve()
    else:
        p = p.resolve()
    return p


class Settings:
    tier: str
    inference_url: str
    model_name: str
    context_length: int
    num_ctx: int | None  # Ollama context window; None = use model default (faster with smaller value)
    num_predict: int | None  # Ollama max new tokens; None = use model default
    index_path: Path
    repo_path: Path
    ingest_max_files: int  # 0 = no limit (full repo); default 500 for faster dev runs
    rag_top_k: int
    max_context_chars: int  # max RAG context chars in prompt (smaller = faster)

    def __init__(self) -> None:
        self.tier = _str("TIER", "dev").lower()
        if self.tier not in TIER_CHOICES:
            self.tier = "dev"
        self.inference_url = _str("INFERENCE_URL", "http://localhost:11434").rstrip("/")
        self.model_name = _str("MODEL_NAME", "llama3.1:8b")
        self.context_length = _int("CONTEXT_LENGTH", 8192)
        _num_ctx = _int("NUM_CTX", 0)
        self.num_ctx = _num_ctx if _num_ctx > 0 else None
        _num_predict = _int("NUM_PREDICT", 0)
        self.num_predict = _num_predict if _num_predict > 0 else None
        self.index_path = _path("INDEX_PATH", "./data/faiss_index")
        self.repo_path = _path("REPO_PATH", "./data/transformers")
        self.ingest_max_files = _int("INGEST_MAX_FILES", 500)
        self.rag_top_k = max(1, min(_int("RAG_TOP_K", 4), 20))
        self.max_context_chars = max(1000, _int("MAX_CONTEXT_CHARS", 8000))

    def __repr__(self) -> str:
        return f"Settings(tier={self.tier!r}, inference_url={self.inference_url!r}, model_name={self.model_name!r})"


settings = Settings()
