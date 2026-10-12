"""
The indexer

Reads the text files and stores them in ChromaDB, one document per file.
Uses the multilingual embedding model intfloat/multilingual-e5-small.
"""

import os

# Silence the sentence-transformers progress bars.
os.environ["TQDM_DISABLE"] = "1"

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from pathlib import Path
from server.config import CONFIG

# E5 expects a marker on stored documents.
EMBEDDING_FUNCTION = SentenceTransformerEmbeddingFunction(
    model_name=CONFIG["embedding_model"]
)
E5_DOCUMENT_PREFIX = "passage: "


def load_text_files(documents_path: Path) -> list[dict]:
    """
    Read every .txt file in the given folder.

    Returns:
        [{"filename": "xxx.txt", "content": "..."}, ...]
    """
    files = []

    for txt_file in documents_path.glob("*.txt"):
        content = txt_file.read_text(encoding="utf-8")
        files.append({
            "filename": txt_file.name,
            "content": content,
        })
        print(f"  read: {txt_file.name} ({len(content)} chars)")

    return files


def index_documents(
    documents_path: Path,
    chroma_path: Path,
    collection_name: str = "documents",
) -> int:
    """
    Index the text files into ChromaDB, one document per file.

    Args:
        documents_path: folder holding the .txt files
        chroma_path: where ChromaDB stores its data
        collection_name: name of the collection

    Returns:
        How many documents were indexed.
    """
    print("=== Indexing ===")
    print(f"Documents: {documents_path}")
    print(f"ChromaDB:  {chroma_path}")

    # 1. Read the files
    print("\n[1] Reading the text files")
    files = load_text_files(documents_path)
    print(f"  -> {len(files)} files read")

    if not files:
        print("Warning: no text files found")
        return 0

    # 2. Open ChromaDB in persistent mode
    print("\n[2] Opening ChromaDB")
    client = chromadb.PersistentClient(path=str(chroma_path))

    # Drop any existing collection and start over. Adding an id that already
    # exists does not overwrite it, so rebuilding in place would not work.
    existing = [c.name for c in client.list_collections()]
    if collection_name in existing:
        client.delete_collection(collection_name)
        print(f"  dropped the existing collection '{collection_name}'")

    collection = client.create_collection(
        name=collection_name,
        embedding_function=EMBEDDING_FUNCTION
    )
    print(f"  created collection '{collection_name}'")
    print(f"  embedding model: {CONFIG['embedding_model']}")

    # 3. Store the files. One file is one document, and its name is its id.
    print("\n[3] Indexing")

    collection.add(
        ids=[f["filename"] for f in files],
        documents=[f'{E5_DOCUMENT_PREFIX}{f["content"]}' for f in files],
        metadatas=[{"source": f["filename"]} for f in files],
    )
    for f in files:
        print(f"  {f['filename']}: {len(f['content'])} chars")

    print(f"\n=== Done: {len(files)} documents indexed ===")
    return len(files)


def main() -> None:
    """Entry point for the rag-index command."""
    index_documents(
        documents_path=CONFIG["documents_path"],
        chroma_path=CONFIG["chroma_path"],
    )


# When run directly
if __name__ == "__main__":
    main()
