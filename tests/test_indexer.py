"""
Tests for the indexer

They use temporary files, so they do not depend on the real data/documents.
"""

import tempfile
from pathlib import Path
import sys

# Add src/server to the import path
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "server"))

from indexer import load_text_files, index_documents
import chromadb


def test_load_text_files():
    """Test reading the text files"""
    # Create the test files in a temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Create files for the test
        (tmppath / "test1.txt").write_text("content of file one", encoding="utf-8")
        (tmppath / "test2.txt").write_text("content of file two", encoding="utf-8")
        (tmppath / "other.md").write_text("this file is ignored", encoding="utf-8")

        # Run the loader
        files = load_text_files(tmppath)

        # Only the two .txt files are read
        assert len(files) == 2

        # The file names and contents come back correctly
        filenames = [f["filename"] for f in files]
        assert "test1.txt" in filenames
        assert "test2.txt" in filenames


def test_index_documents():
    """Test the whole indexing flow"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        docs_path = tmppath / "documents"
        chroma_path = tmppath / "chroma_db"
        docs_path.mkdir()

        # Create documents for the test
        (docs_path / "drinks.txt").write_text(
            "We serve espresso, tea and drinking chocolate.",
            encoding="utf-8"
        )
        (docs_path / "hours.txt").write_text(
            "We open at eight and close at six.",
            encoding="utf-8"
        )

        # Build the index
        total = index_documents(
            documents_path=docs_path,
            chroma_path=chroma_path,
            collection_name="test_collection",
        )

        # One document per file
        assert total == 2

        # Confirm the data was saved into ChromaDB
        client = chromadb.PersistentClient(path=str(chroma_path))
        collection = client.get_collection("test_collection")

        # Searching for "coffee" hits the drinks document
        results = collection.query(query_texts=["coffee"], n_results=1)
        assert "espresso" in results["documents"][0][0]
        assert results["metadatas"][0][0]["source"] == "drinks.txt"


def test_the_id_is_the_file_name():
    """One file is one document, and the file name is its id"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        docs_path = tmppath / "documents"
        docs_path.mkdir()
        (docs_path / "menu.txt").write_text("Espresso and tea.", encoding="utf-8")

        index_documents(
            documents_path=docs_path,
            chroma_path=tmppath / "chroma_db",
            collection_name="test_ids",
        )

        client = chromadb.PersistentClient(path=str(tmppath / "chroma_db"))
        collection = client.get_collection("test_ids")

        assert collection.get()["ids"] == ["menu.txt"]
