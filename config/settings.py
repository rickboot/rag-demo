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
    index_path: Path
    repo_path: Path
    ingest_max_files: int  # 0 = no limit (full repo); default 500 for faster dev runs

    def __init__(self) -> None:
        self.tier = _str("TIER", "dev").lower()
        if self.tier not in TIER_CHOICES:
            self.tier = "dev"
        self.inference_url = _str("INFERENCE_URL", "http://localhost:11434").rstrip("/")
        self.model_name = _str("MODEL_NAME", "llama3.1:8b")
        self.context_length = _int("CONTEXT_LENGTH", 8192)
        self.index_path = _path("INDEX_PATH", "./data/faiss_index")
        self.repo_path = _path("REPO_PATH", "./data/transformers")
        self.ingest_max_files = _int("INGEST_MAX_FILES", 500)

    def __repr__(self) -> str:
        return f"Settings(tier={self.tier!r}, inference_url={self.inference_url!r}, model_name={self.model_name!r})"


settings = Settings()
