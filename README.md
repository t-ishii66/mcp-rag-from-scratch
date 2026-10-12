---
title: "MCP RAG from scratch"
description: "Understand MCP by writing it yourself. Build an MCP server and client by hand, from raw JSON-RPC over stdio to a working RAG loop with ChromaDB and a local LLM on Ollama. Free, open source, educational. English and Japanese."
permalink: /
---
![MCP RAG from scratch](docs/images/top.png)

# MCP RAG from scratch

**English** · [日本語](README-jp.md)

This is hands-on material for **writing MCP and RAG yourself and understanding how they work**.

<!-- SEO intro added by setup-github-pages; review and adjust -->

If you have ever wanted to **build your own MCP server** — see what the
**Model Context Protocol** actually sends on the wire, understand how
**JSON-RPC** and **tool calling** fit together, or learn **RAG** by working
through a small but real example — this course is for you. It covers
**ChromaDB** vector search, sentence embeddings, and running a **local LLM**
with **Ollama**, all on your own machine.

<!-- /SEO intro -->

You may have used an MCP-capable tool, but what happens inside is not visible.
In this project, you write both the client and the server yourself.
We go as far as assembling the JSON-RPC messages by hand, one line at a time.

Everything stays local, and no API key is needed.

---

## Documentation

| # | Page | Contents |
|---|-------|------|
| 1 | [What you need and installing Docker](docs/en/01-setup.md) | Checking the resources you need, and installing Docker |
| 2 | [Docker primer](docs/en/02-docker-basics.md) | Containers, images, volumes, Compose. Skippable if you are used to it |
| 3 | [Setting up a working environment](docs/en/03-environment.md) | The two containers, where the data lives, day-to-day operations, checking that it works |
| 4 | [Running ChromaDB](docs/en/04-chromadb.md) | Reading and running the Step 1 code |
| 5 | [Building the database and preparing a search function](docs/en/05-chromadb-persist.md) | Building it on disk ahead of time, and preparing `search()` |
| 6 | [Speaking MCP in raw JSON-RPC](docs/en/06-mcp-protocol.md) | Step 2. Looking at the protocol one line at a time |
| 7 | [Writing MCP with the SDK](docs/en/07-mcp-sdk.md) | Step 3. Writing the server and the client in code |
| 8 | [Setting up Ollama](docs/en/08-ollama-setup.md) | Downloading the model, and checking that it works on its own |
| 9 | [The relationship between MCP and Ollama](docs/en/09-mcp-and-ollama.md) | The structure of the whole. How the LLM chooses a tool |
| 10 | [Completing RAG](docs/en/10-rag.md) | Step 4. Putting the LLM on, and the whole thing connects |
| 11 | [Running the finished version interactively](docs/en/11-interactive-client.md) | Running the interactive client in `src/`, and looking back over the whole |

1 goes as far as installing Docker. 2 is a primer on Docker itself, and
this project does not appear in it. **You can skip it if you are used to Docker.**

In 3 you set up the environment and confirm it as far as `pytest` passing.

4 and 5 are ChromaDB. **They stop at the extent needed for reading MCP.**
Read through 5, and the search side is complete; MCP starts from Step 2.

6 and 7 are the heart of MCP. From 8 through 10 you put the LLM on, and in 11 you make it interactive.

---

## The code you run

Alongside the chapters, we provide **a single file that runs independently** for each stage.
As you read, run the corresponding Step.

| Step | File | What it builds | LLM |
|------|---------|---------|-----|
| 1 | `steps/01_chromadb.py` | **ChromaDB** — put documents in, and take out the ones close to a question | Not needed |
| 2 | `steps/02_mcp_raw.py` | **MCP** — call that search from another process, in raw JSON-RPC | Not needed |
| 3 | `steps/03_mcp_sdk.py` | **MCP** — write the same thing with the official SDK | Not needed |
| 4 | `steps/04_rag.py` | **RAG** — hand the retrieved documents to the LLM and have it write the answer | Needed |


---

## How to run it

Running and testing happen in a Docker Ubuntu container.

```bash
docker compose up -d
docker compose exec app uv run python steps/01_chromadb.py
```

For setting up the environment, handling Ollama, and what to do when you run into trouble, see
**[What you need and installing Docker](docs/en/01-setup.md)**.
If you are unfamiliar with Docker itself, **[Docker primer](docs/en/02-docker-basics.md)** comes first.

---

## What is being searched

The 7 material files of the fictional cafe **The Wandering Kettle**, in `data/documents/`.

```
allergens.txt      faq.txt           hours_access.txt
menu_drinks.txt    menu_food.txt     staff_handbook.txt
story.txt
```

The menu, opening hours, FAQ, allergy information, notes for staff, and how the shop came about.

The reason it is a shop that does not exist is that if the LLM answers from knowledge it has already learned,
you can no longer tell whether the search is working.

The data is in English, but **you can look things up by asking in Japanese too**.
That is because we use a multilingual embedding model, and this in itself
makes for an easy-to-grasp demonstration that "vector search is not keyword matching".

```bash
docker compose exec app uv run python tools/query_chromadb.py
```

```
query> 犬を連れて行ってもいいですか？

--- Search results (1 items) ---
  [1] distance=0.2449  source=faq.txt
      CAN I STAY AND WORK?

The Wandering Kettle - Questions We Get Asked
...
```

Asked in Japanese, and the English `faq.txt` was retrieved.
Since **one file is one item**, what comes back is the whole file. The part about dogs is inside it.

Swap out the `.txt` files in `data/documents/`, and it becomes a search tool for a different purpose as it is.

---

## Tech stack

| Category | What is used |
|---------|---------|
| Language | Python 3.11+ |
| MCP | The `mcp` official Python SDK v2 |
| Vector DB | ChromaDB |
| Embedding model | `intfloat/multilingual-e5-small` |
| LLM | Ollama (Step 4 only) |
| Package management | uv |
| Runtime environment | Docker (Ubuntu 24.04) |

---

## Tests

```bash
docker compose exec app uv run pytest
```

They all pass even without Ollama.
