"""Run the backend: uv run python -m backend"""
import os
import warnings

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
warnings.filterwarnings("ignore", message=".*resource_tracker.*leaked semaphore.*", category=UserWarning)

import uvicorn

from backend.main import app

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
