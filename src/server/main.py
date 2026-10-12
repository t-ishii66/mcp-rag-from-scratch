"""
The MCP server

Offers three tools over ChromaDB, spoken over stdio as JSON-RPC 2.0.

Debug mode:
  Start with RAG_DEBUG=1 to print what the server is doing to stderr.
"""

import sys
import os

# Silence the sentence-transformers progress bars.
os.environ["TQDM_DISABLE"] = "1"

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

# From MCP SDK v2. FastMCP of v1 is gone, replaced by MCPServer.
from mcp.server.mcpserver import MCPServer

from server.config import CONFIG

DEBUG = os.environ.get("RAG_DEBUG", "").lower() in ("1", "true", "yes")


def debug_log(message: str) -> None:
    """Log to stderr. stdout belongs to the JSON-RPC traffic and must stay clean."""
    if DEBUG:
        print(f"[DEBUG] {message}", file=sys.stderr)


mcp = MCPServer("rag-search-server")

# The same multilingual model the indexer used. E5 wants a prefix on the query.
EMBEDDING_FUNCTION = SentenceTransformerEmbeddingFunction(
    model_name=CONFIG["embedding_model"]
)
E5_QUERY_PREFIX = "query: "
E5_DOCUMENT_PREFIX = "passage: "

# Connected on the first search rather than at import time.
_collection = None


def get_collection():
    """Return the ChromaDB collection, connecting on first use."""
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=str(CONFIG["chroma_path"]))
        _collection = client.get_collection(
            "documents",
            embedding_function=EMBEDDING_FUNCTION,
        )
        debug_log(f"connected to ChromaDB at {CONFIG['chroma_path']}")
    return _collection


@mcp.tool()
def search(query: str, top_k: int = 5) -> str:
    """
    Search the documents of a cafe called The Wandering Kettle.

    Use this to answer questions about the menu, prices, opening hours,
    location, wifi and power sockets, allergies and dietary options, the
    staff handbook, and the history of the shop.

    Args:
        query: What to search for, e.g. "opening hours" or "can I bring a dog"
        top_k: How many results to return (default: 5)

    Returns:
        The matching passages, with the source file name and distance score.
    """
    # This docstring becomes the tool definition that travels over MCP, so it
    # is written for the model that will read it.
    debug_log(f"search() called with query='{query}', top_k={top_k}")

    print("embedding the query...", file=sys.stderr)
    collection = get_collection()
    results = collection.query(
        query_texts=[f"{E5_QUERY_PREFIX}{query}"],
        n_results=top_k,
    )

    # ChromaDB nests one list per query around one list per result. Only one
    # query was sent, hence the [0]:
    #
    # results = {
    #   "documents": [["WHEN WE ARE OPEN Monday: 8:00 to...", "Dogs are welcome..."]],
    #   "metadatas": [[{"source": "hours_access.txt"}, {...}]],
    #   "distances": [[0.15, 0.19]],   # smaller is closer
    #   "ids": [["hours_access.txt", "faq.txt"]],
    # }
    #
    documents = results["documents"][0] if results["documents"] else []
    metadatas = results["metadatas"][0] if results["metadatas"] else []
    distances = results["distances"][0] if results["distances"] else []

    debug_log(f"{len(documents)} results")

    # Format the results as one block of text. The model reads this directly,
    # so it is prose rather than structured data.
    output_lines = []
    for i, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances)):
        source = meta.get("source", "unknown")
        # Smaller distance means closer. ChromaDB defaults to cosine distance.
        output_lines.append(f"[{i+1}] source: {source} (distance: {dist:.2f})")
        output_lines.append(doc)
        output_lines.append("")

    if not output_lines:
        return "No matching passages were found."

    return "\n".join(output_lines)


@mcp.tool()
def list_documents() -> str:
    """
    List the names of the document files that can be searched.

    Use this when the question is about what information is available,
    not about the contents of the cafe documents.

    Returns:
        The file names, one per line.
    """
    debug_log("list_documents() called")

    collection = get_collection()
    return "\n".join(sorted(collection.get()["ids"]))


@mcp.tool()
def get_document(name: str) -> str:
    """
    Return one document file in full, by its exact file name.

    Use this when the file name is already known, for example from
    list_documents. To find something by meaning, use search instead.

    Args:
        name: The file name, e.g. "faq.txt"

    Returns:
        The whole text of that file.
    """
    debug_log(f"get_document() called with name='{name}'")

    collection = get_collection()
    result = collection.get(ids=[name])

    # The model picks the name, so a wrong one is an ordinary case here.
    if not result["documents"]:
        return f"There is no document named {name}."

    # Strip the prefix the indexer added for the embedding model.
    return result["documents"][0].removeprefix(E5_DOCUMENT_PREFIX)


if __name__ == "__main__":
    debug_log("MCP server starting")
    debug_log(f"ChromaDB path: {CONFIG['chroma_path']}")

    # Start speaking JSON-RPC over stdio.
    mcp.run()
