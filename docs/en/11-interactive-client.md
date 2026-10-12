---
title: "Running the finished version interactively"
description: "This is the final chapter. The four scripts in steps/ were each a script with one question embedded in it. In src/ there is a finished version that does the sam…"
lang: en
---

# Running the finished version interactively

This is the final chapter. The four scripts in `steps/` were each a script with one question embedded in it.
In `src/` there is **a finished version that does the same mechanism interactively**.

Let's run it while asking our own questions, and look one more time at what is happening inside.

## Running it interactively

From here on it is the finished version, `src/client/main.py`.
The flow is as in [the sequence diagram in chapter 9](09-mcp-and-ollama.md#what-happens-for-a-single-question), and
this is that turned into an interactive form as it is.

```bash
docker compose exec app uv run python -m client.main
```

```
=== MCP RAG client ===
LLM: qwen3:1.7b
Type 'quit' to leave.

[1] Connected to the MCP server
[2] Tools reported by the server: ['search', 'list_documents', 'get_document']
[3] Converted the tool definitions for the LLM

From here on, every question is sent to the LLM along with the tools.

Question: Can I bring my dog?
  -> sending the question and the tools to the LLM...
  -> tool call: search({'top_k': 5, 'query': 'can I bring a dog'})
  -> got the search results
  -> asking the LLM to answer from them...

[Answer]
Yes, you can bring your dog. The Wandering Kettle allows dogs on the small
terrace at the top of the stairs but not inside the room itself. There is a
water bowl by the terrace door, and assistance animals are welcome anywhere.

Question: What documents can you search?
  -> sending the question and the tools to the LLM...
  -> tool call: list_documents({})
  -> got the search results
  -> asking the LLM to answer from them...

[Answer]
The documents that can be searched are:

- allergens.txt
- faq.txt
- hours_access.txt
- menu_drinks.txt
- menu_food.txt
- staff_handbook.txt
- story.txt

Question: quit
Bye.
```

Startup takes 10 to 20 seconds, and one question takes from tens of seconds to several minutes. That is because inference runs on the CPU,
and most of the waiting is the two queries to the LLM (chapter 10).

**With the two questions, the tools that got called differ.** The first question is `search`, the second is `list_documents`.
The client is not choosing. **The LLM chose from the three that were handed over and returned that name**, nothing more.

### The three lines at startup

Before accepting questions, the client has finished three things.

| Display | Contents | Where we saw it |
|------|------|------------|
| `[1] Connected to the MCP server` | Started the server and sent `initialize` | Chapters 6 and 7 |
| `[2] Tools reported by the server: [...]` | The result of `tools/list`. Three come back | Chapters 6 and 7 |
| `[3] Converted the tool definitions for the LLM` | Repacking into Ollama's format | Chapter 9 |

**The LLM has not appeared up to here.** The connection and the confirmation of the tools finish with MCP alone.

### What happens every time you ask a question

The lines that are displayed are the order of the processing, as they are.

| Display | What it is doing |
|------|--------------|
| `-> sending the question and the tools to the LLM...` | The first POST (the judgment) |
| `-> tool call: search({...})` | The `tool_calls` that came back |
| `-> got the search results` | The result of `tools/call` |
| `-> asking the LLM to answer from them...` | The second POST (the writing) |

Type `quit` and it ends. Since the `async with` is left, the MCP server exits along with it.

### Ask another question, and it does not remember the last one

Ollama does not remember the previous `messages`. If you want to continue the conversation,
you line up **all** of the past exchanges in `messages` and send them every time.

On the MCP side, the session was continuing (chapter 7). **Even with the same word "connection", the nature differs.**

| | Where the state is |
|---|---|
| MCP server | While the connection is open, the correspondence with the client continues |
| Ollama | Nowhere. A one-off POST every time |

This material's client holds no conversation history. Questions are independent, one by one.
**That is because the purpose is to follow the flow of MCP and the search, and conversation management has nothing to do with that.**

### Peeking at the JSON-RPC

Add `RAG_DEBUG=1`, and the JSON being exchanged with the MCP server comes out as it is.

```bash
docker compose exec app env RAG_DEBUG=1 uv run python -m client.main
```

```
[JSON-RPC] -> sent: tools/list
{
  "method": "tools/list"
}

[JSON-RPC] <- received: tools/list
{
  "tools": [
    {
      "name": "search",
      "description": "\nSearch the documents of a cafe called The Wandering Kettle.\n\nUse this to answer questions about the menu, prices, opening hours,\nlocation, wifi and power sockets, allergies and dietary options, the\ns...",
      "inputSchema": {
        "properties": {
          "query": {"title": "Query", "type": "string"},
          "top_k": {"default": 5, "title": "Top K", "type": "integer"}
        },
        "required": ["query"],
        "type": "object",
        "title": "searchArguments"
      }
    },
    { "name": "list_documents", ... },
    { "name": "get_document",   ... }
  ]
}

[2] Tools reported by the server: ['search', 'list_documents', 'get_document']
[3] Converted the tool definitions for the LLM

Question: Can I bring my dog?
  -> sending the question and the tools to the LLM...
  -> tool call: search({'top_k': 5, 'query': 'can I bring a dog'})

[JSON-RPC] -> sent: tools/call
{
  "method": "tools/call",
  "params": {
    "name": "search",
    "arguments": {"top_k": 5, "query": "can I bring a dog"}
  }
}

[JSON-RPC] <- received: tools/call
{
  "content": [
    {
      "type": "text",
      "text": "[1] source: faq.txt (distance: 0.21)\npassage: \nThe Wandering Kettle - Questions We Get Asked\n\nCAN I STAY AND WORK?\n\nYes, on most days. We ask for one order every ninety minutes, and we ask you\nto move..."
    }
  ]
}
```

The same shapes we saw in chapter 6 are flowing.
Long strings are cut at 200 characters for display (`debug_jsonrpc()`).
Before this, the `initialize` exchange is displayed too, but it is omitted here.
The same goes for the definitions of the remaining two tools.

## What comes next

**At this point, you have one RAG running on MCP on your machine.** Here are three ways to extend it.

- **Swap the material.** Replace `data/documents/` with your own text and re-index, and
  it becomes an LLM with search for your own use (chapter 5)
- **Add more tools.** Write one more function with `@mcp.tool()` attached, and that alone adds one (chapter 7).
  Which one the LLM chooses is decided by how the docstring is written
- **Change the model.** Just make sure it supports tool calling (chapters 8 and 9)
