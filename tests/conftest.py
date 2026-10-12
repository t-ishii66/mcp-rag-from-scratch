"""
Shared fixtures and setup for the tests

Before any test runs, rebuild the ChromaDB index.
"""

import pytest
import shutil
from pathlib import Path

# uv sync installs the project in editable mode, so server / client can be
# imported directly without touching sys.path.
from server.indexer import index_documents
from server.config import CONFIG


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Initialize the ChromaDB used by the tests"""
    chroma_path = Path(CONFIG["chroma_path"])
    documents_path = Path(CONFIG["documents_path"])

    # ChromaDB for the tests (rebuilt from scratch on every test run)
    #
    # Delete the contents only, not the directory itself.
    # Under Docker this directory is a volume mount point,
    # so the directory itself cannot be removed.
    if chroma_path.exists():
        for child in chroma_path.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    else:
        chroma_path.mkdir(parents=True, exist_ok=True)

    # Build the index
    if documents_path.exists():
        print(f"\nInitializing test DB: building the index from {documents_path}")
        index_documents(
            documents_path=documents_path,
            chroma_path=chroma_path,
        )

    yield

    # No cleanup needed after the tests (the next run resets everything)
