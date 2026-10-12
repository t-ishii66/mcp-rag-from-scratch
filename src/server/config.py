"""
Settings

Read from the environment when set, otherwise fall back to a default.
Kept as one plain dictionary.
"""

import os
from pathlib import Path

# The project root, two levels above this file.
PROJECT_ROOT = Path(__file__).parent.parent.parent

CONFIG = {
    # Where the text files live
    "documents_path": Path(os.environ.get(
        "RAG_DOCUMENTS_PATH",
        PROJECT_ROOT / "data" / "documents"
    )),

    # Where ChromaDB keeps its data
    "chroma_path": Path(os.environ.get(
        "RAG_CHROMA_PATH",
        PROJECT_ROOT / "chroma_db"
    )),

    # Which model Ollama should run
    "ollama_model": os.environ.get("OLLAMA_MODEL", "qwen3:1.7b"),

    # The embedding model. Downloaded from Hugging Face on first use, ~470MB.
    "embedding_model": "intfloat/multilingual-e5-small",
}
