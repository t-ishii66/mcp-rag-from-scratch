"""
Tests that check how ChromaDB behaves

What these tests confirm:
1. Documents can be added
2. Vector search (similarity search) works
3. Metadata (such as the file name) can be stored and read back
"""

import chromadb
from pathlib import Path


def test_basic_add_and_search():
    """Confirm that data can be put into ChromaDB and searched"""

    # === 1. Create a ChromaDB client ===
    # Use in-memory mode (no persistence) to keep it simple
    client = chromadb.Client()

    # === 2. Create a collection (similar to a table) ===
    collection = client.create_collection(name="test_cafe")

    # === 3. Add documents ===
    # ChromaDB turns the text into vectors for us
    collection.add(
        ids=["doc1", "doc2", "doc3"],  # unique IDs
        documents=[
            "Dogs are welcome on the small terrace.",
            "We are closed every Wednesday for roasting.",
            "Oat milk and soy milk are available at no extra charge.",
        ],
        metadatas=[  # extra information (file name and so on)
            {"source": "faq.txt"},
            {"source": "hours_access.txt"},
            {"source": "allergens.txt"},
        ],
    )

    # === 4. Run a similarity search ===
    # The query words do not appear in the text, but the meaning matches
    results = collection.query(
        query_texts=["Can I bring my pet?"],
        n_results=2,  # take the top 2 hits
    )

    # === 5. Check the results ===
    # Shape of the results: results["documents"][0] = the result list for the first query
    print("Search results:")
    print(f"  1st: {results['documents'][0][0]}")
    print(f"  2nd: {results['documents'][0][1]}")

    # Confirm that the sentence about dogs comes back
    top_result = results["documents"][0][0]
    assert "Dogs" in top_result


def test_get_filename_from_metadata():
    """Confirm that the file name (the source) can be read from a search result"""

    client = chromadb.Client()
    collection = client.create_collection(name="test_metadata")

    # Metadata is stored together with the document when it is added
    collection.add(
        ids=["1"],
        documents=["The soup of the day is written on the slate by the register."],
        metadatas=[{"source": "menu_food.txt", "topic": "soup"}],
    )

    # Search
    results = collection.query(query_texts=["what soup is there"], n_results=1)

    # Read the metadata
    metadata = results["metadatas"][0][0]
    print(f"Source file: {metadata['source']}")
    print(f"Topic: {metadata['topic']}")

    assert metadata["source"] == "menu_food.txt"
    assert metadata["topic"] == "soup"


def test_search_real_text_files():
    """Load the real files in data/documents/ and search them"""

    # Where the text files live
    docs_dir = Path(__file__).parent.parent / "data" / "documents"

    if not docs_dir.exists():
        print(f"Skipped: {docs_dir} does not exist")
        return

    # Read the text files
    txt_files = list(docs_dir.glob("*.txt"))
    if not txt_files:
        print("Skipped: there are no text files")
        return

    print(f"Files found: {[f.name for f in txt_files]}")

    # Register them in ChromaDB
    client = chromadb.Client()
    collection = client.create_collection(name="real_docs")

    for i, txt_file in enumerate(txt_files):
        content = txt_file.read_text(encoding="utf-8")
        collection.add(
            ids=[f"doc_{i}"],
            documents=[content],
            metadatas=[{"source": txt_file.name}],
        )

    print(f"Number of documents registered: {collection.count()}")

    # Search test
    results = collection.query(query_texts=["dogs"], n_results=1)

    print(f"Search result: {results['metadatas'][0][0]['source']}")
    assert collection.count() == len(txt_files)
