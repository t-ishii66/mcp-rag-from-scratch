# Building the database and preparing a search function

![Alice and Bob playing with paper boats on the water](../images/alice-bob-paper-boats.png)

The database in the previous chapter was in memory. It disappears when the run finishes,
so it was re-vectorizing the 7 files every time it started.

Build it on disk ahead of time, and that initialization is no longer needed.
It can also be opened from another program.

There are two things to do in this chapter.

1. Build the database on disk (`/opt/chroma_db` inside the container)
2. Prepare **a search function that takes a string and returns a string**

## From memory to disk — only one line changes

Step 1 was like this.

```python
def get_collection():
    client = chromadb.Client()                    # In memory. It disappears when it exits
    return client.create_collection(name="cafe")
```

To put it on disk, you only change the kind of client.

```python
def get_collection():
    client = chromadb.PersistentClient(path=chroma_path)   # ← this is the only difference
    return client.create_collection(name="documents")
```

(Only the essential points are extracted here. In the actual code, the building side is in
`indexer.py` and the searching side is in `main.py`)

## Building the database

```bash
docker compose exec app uv run python -m server.indexer
```

```
=== Indexing ===
Documents: /workspace/data/documents
ChromaDB:  /opt/chroma_db

[1] Reading the text files
  read: staff_handbook.txt (1693 chars)
  read: faq.txt (1642 chars)
  ...
  -> 7 files read

[2] Opening ChromaDB
  created collection 'documents'
  embedding model: intfloat/multilingual-e5-small

[3] Indexing
  staff_handbook.txt: 1693 chars
  ...

=== Done: 7 documents indexed ===
```

7 items. Same as Step 1, **one file is one item**.

**Run this command only once.** What it builds stays on disk, so
from then on you only need to search. Run it again when you rewrite `data/documents/`.

> [!NOTE]
> **Rebuilding**
>
> To rebuild the ChromaDB database, run the following commands.
>
> ```bash
> docker compose exec app sh -c 'rm -rf /opt/chroma_db/*'
> docker compose exec app uv run python -m server.indexer
> ```

### Where it is stored

It is placed at `/opt/chroma_db`. Not directly under the project, but at a separate place inside the container.

In `docker-compose.yml`, this is made into a **named volume**.

```yaml
services:
  app:
    volumes:
      - .:/workspace               # Edits on the host show up in the container
      - chroma-db:/opt/chroma_db   # Keep ChromaDB outside /workspace
    environment:
      RAG_CHROMA_PATH: /opt/chroma_db

volumes:
  chroma-db:
```

`/workspace` shows the host's project as it is (a bind mount).
`chroma-db`, on the other hand, is an area Docker manages, and it does not appear in the host's file tree.


The storage location is not hard-coded; it is passed in with `RAG_CHROMA_PATH`.

```bash
docker compose exec app ls /opt/chroma_db
```

```
a33eb2fc-516c-47ce-a4c0-3b3cd66ec7ce
chroma.sqlite3
```

`chroma.sqlite3` holds the bodies and the metadata, and the UUID directory is the vector index.

## Preparing the search function

In `src/server/main.py` there is the function that searches.

```python
def search(query: str, top_k: int = 5) -> str:
    collection = get_collection()
    results = collection.query(
        query_texts=[f"{E5_QUERY_PREFIX}{query}"],
        n_results=top_k,
    )

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    output_lines = []
    for i, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances)):
        source = meta.get("source", "unknown")
        output_lines.append(f"[{i+1}] source: {source} (distance: {dist:.2f})")
        output_lines.append(doc)
        output_lines.append("")

    return "\n".join(output_lines)
```

`get_collection()` **opens the collection that was built ahead of time**.
It is not `create_collection()`. The searching side does not build anything.

For each item, it piles 3 lines into `output_lines`: a heading, the body, and a blank line.
Look things up with `top_k=2`, and it comes out like this.

```python
output_lines = [
    '[1] source: hours_access.txt (distance: 0.16)',
    'passage: The Wandering Kettle - Hours and Directions\n\nWHEN WE ARE OPEN\n\n...',
    '',
    '[2] source: staff_handbook.txt (distance: 0.18)',
    'passage: The Wandering Kettle - Notes for Staff\n\nOPENING\n\nArrive forty...',
    '',
]
```

At the end, `"\n".join()` makes it into a single string.

What it does is the same `query()` call as in the previous chapter; the difference is **the shape of the return value**.

```
search(query: str, top_k: int = 5) -> str
```

**It takes a string and returns one formatted string.** It returns neither a dictionary nor an array.

Since the formatting is already done, **the calling side does not need to know the structure of the results**.
There is no need to follow a doubly nested list, nor to round the distances.
A function that takes a string and returns a string becomes a part that other programs can call as it is.

What comes back is a string like this.

```
[1] source: hours_access.txt (distance: 0.16)
passage: The Wandering Kettle - Hours and Directions

WHEN WE ARE OPEN

Monday: 8:00 to 18:00
Tuesday: 8:00 to 18:00
...

[2] source: staff_handbook.txt (distance: 0.18)
...
```

## Trying out the search

There is a tool that queries ChromaDB directly, without going through the function.

```bash
docker compose exec app uv run python tools/query_chromadb.py
```

```
Using the existing ChromaDB: /opt/chroma_db
--------------------------------------------------
Collections: ['documents']
Collection in use: documents (7 items)
--------------------------------------------------
Enter a search query (type quit to exit)

query> opening hours

--- Search results (1 items) ---
  [1] distance=0.1608  source=hours_access.txt
      WHEN WE ARE OPEN
      The Wandering Kettle - Hours and Directions
      ...
```

It says `Using the existing ChromaDB`. It has not rebuilt anything.
The only thing being vectorized is the query you are about to type.

The default is 1 item. Add ` /number` at the end to increase it (`opening hours /3`).
`quit` exits.

### "No match" never comes back

```
query> quantum physics

--- Search results (1 items) ---
  [1] distance=0.2254  source=faq.txt
```

There is nothing about quantum mechanics in the cafe's material. Even so, **something always ends up in 1st place**.
Vector search only "returns the nearest thing"; it does not judge "whether it is near enough".

This property comes into play in Step 4, when we put the LLM on top.
Hand it an unrelated document, and the LLM will still try to answer something.

## Swapping in your own data

Replace the 7 cafe files in `data/documents/` with your own `.txt` files.
You only need to delete and place them on the host side. It is a bind mount, so they are visible from the container as they are.

```bash
# 1. On the host side, delete the cafe material and place your own files
rm data/documents/*.txt
cp ~/my-notes/*.txt data/documents/

# 2. Delete the old database and rebuild it
docker compose exec app sh -c 'rm -rf /opt/chroma_db/*'
docker compose exec app uv run python -m server.indexer

# 3. Try looking things up
docker compose exec app uv run python tools/query_chromadb.py
```

As long as they are `.txt`, the contents can be anything. Japanese can be retrieved too.

## What we have learned so far

- The difference between memory and disk is only `Client()` versus `PersistentClient(path=...)`
- The building side uses `create_collection()`, the searching side uses `get_collection()`
- The search function **takes a string and returns a string**. The calling side need not know the structure inside
- The connection is deferred until the first call

**The search side is complete here.** In the next Step 2, we
**call the `search()` we have just prepared from another process**.
The substance of the search does not change. What changes is only how it is called.
