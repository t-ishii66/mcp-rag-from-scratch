"""
Interactive ChromaDB query tool

It re-reads data/documents to build the ChromaDB index, then lets you send any
query you like and look at the results.
It uses a multilingual embedding model (intfloat/multilingual-e5-small).
Type "quit" or press Ctrl+C to exit.

Usage:
    uv run python tools/query_chromadb.py
"""

import os

# Suppress the tqdm progress bar from sentence-transformers
os.environ["TQDM_DISABLE"] = "1"

from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from server.indexer import index_documents
from server.config import CONFIG

# Multilingual embedding model (E5 models expect a prefix)
EMBEDDING_FUNCTION = SentenceTransformerEmbeddingFunction(
    model_name=CONFIG["embedding_model"]
)
E5_QUERY_PREFIX = "query: "

# Where ChromaDB is stored (taken from CONFIG; the RAG_CHROMA_PATH env var can change it)
CHROMA_PATH = Path(CONFIG["chroma_path"])


def main():
    # === Build the index if it does not exist yet ===
    if not CHROMA_PATH.exists():
        print(f"ChromaDB not found. Building the index: {CHROMA_PATH}")
        print(f"Indexing the documents ({CONFIG['documents_path']})...")
        index_documents(
            documents_path=Path(CONFIG["documents_path"]),
            chroma_path=CHROMA_PATH,
        )
    else:
        print(f"Using the existing ChromaDB: {CHROMA_PATH}")
    print("-" * 50)

    # === Once it is ready, start the interactive query loop ===
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))

    # Show the list of collections
    collections = client.list_collections()
    print(f"Collections: {[c.name for c in collections]}")

    if not collections:
        print("Error: there are no collections.")
        return

    # Use the first collection (normally there is only one)
    # Pass embedding_function explicitly so queries are embedded with the same
    # model that was used when the data was stored
    collection_name = collections[0].name
    collection = client.get_collection(
        name=collection_name,
        embedding_function=EMBEDDING_FUNCTION
    )
    print(f"Collection in use: {collection.name} ({collection.count()} items)")
    print("-" * 50)
    print("Enter a search query (type quit to exit)")
    print()

    while True:
        try:
            query = input("query> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting")
            break

        if not query or query == "quit":
            print("Exiting")
            break

        # Top hit only by default. "opening hours /3" asks for three.
        n_results = 1
        if " /" in query:
            parts = query.rsplit(" /", 1)
            query = parts[0]
            try:
                n_results = int(parts[1])
            except ValueError:
                pass

        # Run the search
        results = collection.query(
            query_texts=[f"{E5_QUERY_PREFIX}{query}"],
            n_results=n_results,
        )

        # Show the results
        docs = results["documents"][0]
        distances = results["distances"][0]
        metadatas = results["metadatas"][0]

        print(f"\n--- Search results ({len(docs)} items) ---")
        for i, (doc, dist, meta) in enumerate(zip(docs, distances, metadatas)):
            source = meta.get("source", "unknown")
            # Strip the E5 prefix before displaying
            display_doc = doc.replace("passage: ", "", 1)
            # Show the first heading found in the file. Headings in these
            # documents are short all-caps lines such as "ANIMALS".
            heading = ""
            for line in display_doc.splitlines():
                stripped = line.strip()
                if stripped and stripped == stripped.upper() and len(stripped) < 40:
                    heading = stripped
                    break
            # If the text is long, cut it at 300 characters
            preview = display_doc[:300] + "..." if len(display_doc) > 300 else display_doc
            print(f"  [{i+1}] distance={dist:.4f}  source={source}")
            if heading:
                print(f"      {heading}")
            print(f"      {preview}")
        print()


if __name__ == "__main__":
    main()
