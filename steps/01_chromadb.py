"""
Step 1: ChromaDB, on its own

Put documents in, get the closest ones back. No MCP and no LLM.

    uv run python steps/01_chromadb.py

ChromaDB is used in four calls, and that is the whole of it:

    chromadb.Client()            open the database
    client.create_collection()   make a collection
    collection.add()             store the documents
    collection.query()           search with a question

It runs standalone. The database is in memory, so nothing is left behind.
"""

import os

# Silence the sentence-transformers progress bars so the output stays readable.
os.environ["TQDM_DISABLE"] = "1"

from pathlib import Path

import chromadb
import numpy as np
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

DOCUMENTS_PATH = Path(__file__).parent.parent / "data" / "documents"

EMBEDDING_MODEL = "intfloat/multilingual-e5-small"

# E5 models expect stored text and queries to carry different markers.
DOCUMENT_PREFIX = "passage: "
QUERY_PREFIX = "query: "


def search(collection, question: str, top_k: int = 3) -> dict:
    """Run one query and print the hits. Returns the raw result."""
    results = collection.query(
        query_texts=[QUERY_PREFIX + question],
        n_results=top_k,
    )

    print(f"\n  Question: {question}")
    for doc_id, distance in zip(results["ids"][0], results["distances"][0]):
        print(f"    distance {distance:.3f}  {doc_id}")

    return results


def main() -> None:
    # =========================================================================
    # [1] Read the text files. One file becomes one document.
    # =========================================================================
    files = []
    for txt_file in sorted(DOCUMENTS_PATH.glob("*.txt")):
        content = txt_file.read_text(encoding="utf-8")
        files.append({"filename": txt_file.name, "content": content})

    print(f"[1] Read {len(files)} files from {DOCUMENTS_PATH}")

    # =========================================================================
    # [2] Store them. ChromaDB calls the embedding function for us, so what
    #     goes in is a list of strings, not a list of vectors.
    # =========================================================================
    embedding_function = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)

    # Client() rather than PersistentClient(): the database lives in memory.
    collection = chromadb.Client().create_collection(
        name="cafe",
        embedding_function=embedding_function,
    )

    collection.add(
        ids=[f["filename"] for f in files],
        documents=[DOCUMENT_PREFIX + f["content"] for f in files],
    )

    stored = collection.get(ids=[files[0]["filename"]], include=["embeddings"])
    dimensions = len(stored["embeddings"][0])
    print(f"[2] Stored {collection.count()} documents as {dimensions}-dimensional vectors")

    # =========================================================================
    # [3] Search
    # =========================================================================
    print("\n[3] Search")
    search(collection, "What time do you close on Friday?")

    # =========================================================================
    # [4] The words in the question do not have to appear in the file
    # =========================================================================
    print("\n[4] The query words do not have to appear in the text")
    results = search(
        collection,
        "I want something warm to drink because it is freezing outside",
        top_k=1,
    )

    text = results["documents"][0][0].lower()
    for word in ("warm", "freezing", "outside"):
        print(f'    "{word}" appears in that file: {word in text}')

    # =========================================================================
    # [5] What the reported distance actually is: cosine distance, which is
    #     1 minus how closely the two vectors point the same way.
    # =========================================================================
    print("\n[5] Work out the distance by hand")
    question = "Do you have oat milk?"
    results = search(collection, question, top_k=1)

    query_vector = np.array(embedding_function([QUERY_PREFIX + question])[0])
    hit_vector = np.array(
        collection.get(ids=[results["ids"][0][0]], include=["embeddings"])["embeddings"][0]
    )
    manual = 1.0 - np.dot(query_vector, hit_vector) / (
        np.linalg.norm(query_vector) * np.linalg.norm(hit_vector)
    )

    print(f"    reported by ChromaDB: {results['distances'][0][0]:.6f}")
    print(f"    computed with numpy : {manual:.6f}")


if __name__ == "__main__":
    main()
