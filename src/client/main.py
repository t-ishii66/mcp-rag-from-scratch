"""
The MCP client

Connects to the MCP server, asks Ollama which tool to call, runs it, and has
Ollama write the answer from what came back.

Usage:
  uv run python -m client.main
"""

import json
import os
import asyncio
import subprocess
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from server.config import CONFIG

# Debug mode. Prints the JSON-RPC traffic.
DEBUG = os.environ.get("RAG_DEBUG", "").lower() in ("1", "true", "yes")


def debug_jsonrpc(direction: str, method: str, data: dict) -> None:
    """Print the JSON-RPC traffic, in debug mode only."""
    if not DEBUG:
        return

    # Walk a copy of the data, shortening anything long.
    def truncate_strings(obj, max_len: int = 200):
        if isinstance(obj, str) and len(obj) > max_len:
            return obj[:max_len] + "..."
        if isinstance(obj, dict):
            return {k: truncate_strings(v, max_len) for k, v in obj.items()}
        if isinstance(obj, list):
            return [truncate_strings(item, max_len) for item in obj]
        return obj

    truncated = truncate_strings(data)
    formatted = json.dumps(truncated, indent=2, ensure_ascii=False)
    print(f"\n[JSON-RPC] {direction}: {method}")
    print(formatted)
    print()


# =============================================================================
# The LLM
# =============================================================================

def call_llm(message: str, tools: list[dict]) -> dict:
    """Ask Ollama which tool to call, if any."""
    import ollama
    # Thinking is left on here. qwen3:1.7b picks the tool far more reliably
    # when it is allowed to reason first.
    response = ollama.chat(
        model=CONFIG["ollama_model"],
        messages=[{"role": "user", "content": message}],
        tools=tools,
    )
    return response


def generate_answer(context: str, question: str) -> str:
    """Ask Ollama to answer from the retrieved passages."""
    import ollama
    # The documents are English and so is this prompt, which is enough for the
    # answer to come back in English. Detecting a language and switching on it
    # would add a concern that has nothing to do with MCP or retrieval.
    prompt = f"""Answer the question using only the reference material below.

[Reference]
{context}

[Question]
{question}

[Answer]"""

    # Nothing to decide here, only prose to write, so thinking is turned off.
    # It costs about twenty seconds on this model.
    response = ollama.chat(
        model=CONFIG["ollama_model"],
        messages=[{"role": "user", "content": prompt}],
        think=False,
    )
    return response["message"]["content"]


# =============================================================================
# Converting MCP tool definitions into Ollama's format
# =============================================================================

def mcp_tools_to_ollama_format(mcp_tools: list) -> list[dict]:
    """
    Convert the tools reported by the MCP server into Ollama's format.

    From MCP:
        Tool(name="search", description="...", input_schema={...})

    To Ollama:
        {"type": "function", "function": {"name": "search", "description": "...", "parameters": {...}}}

    Note that SDK v2 renamed the Python attribute to input_schema, while the
    JSON on the wire still says inputSchema, as the specification requires.
    """
    ollama_tools = []
    for tool in mcp_tools:
        ollama_tools.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.input_schema,
            }
        })
    return ollama_tools


# =============================================================================
# Main
# =============================================================================

async def run_client():
    """Connect, list the tools, then loop on questions."""

    # How to start the server. uv sync installs this project as editable,
    # so PYTHONPATH is not needed.
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "-m", "server.main"],
        env=dict(os.environ),
    )

    print("=== MCP RAG client ===")
    print(f"LLM: {CONFIG['ollama_model']}")
    print("Type 'quit' to leave.")
    print()

    # Connect to the MCP server. The server logs to stderr, which would mix
    # into this session, so it is dropped.
    async with stdio_client(server_params, errlog=subprocess.DEVNULL) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize
            debug_jsonrpc("-> sent", "initialize", {
                "method": "initialize",
                "params": {"capabilities": {}},
            })
            init_result = await session.initialize()
            debug_jsonrpc("<- received", "initialize", {
                "serverInfo": {"name": init_result.server_info.name},
                "capabilities": str(init_result.capabilities),
            })
            print("[1] Connected to the MCP server")

            # Ask what tools it has (tools/list)
            debug_jsonrpc("-> sent", "tools/list", {
                "method": "tools/list",
            })
            tools_result = await session.list_tools()
            mcp_tools = tools_result.tools
            debug_jsonrpc("<- received", "tools/list", {
                "tools": [
                    # Printed as inputSchema to match the wire format. Only
                    # the Python attribute was renamed to input_schema.
                    {"name": t.name, "description": t.description, "inputSchema": t.input_schema}
                    for t in mcp_tools
                ],
            })
            print(f"[2] Tools reported by the server: {[t.name for t in mcp_tools]}")

            # Convert them into the shape the LLM expects
            ollama_tools = mcp_tools_to_ollama_format(mcp_tools)
            print("[3] Converted the tool definitions for the LLM")
            print()
            print("From here on, every question is sent to the LLM along with the tools.")
            print()

            # The conversation loop
            while True:
                # Read a question
                try:
                    user_input = input("Question: ").strip()
                except EOFError:
                    break

                if not user_input:
                    continue
                if user_input.lower() == "quit":
                    print("Bye.")
                    break

                # Send the question and the tools to the LLM
                print("  -> sending the question and the tools to the LLM...")
                response = call_llm(user_input, tools=ollama_tools)

                # The LLM decides: call a tool, or answer directly
                tool_calls = response.get("message", {}).get("tool_calls", [])

                if tool_calls:
                    # It asked for the tool, so search through the server
                    tool_call = tool_calls[0]
                    func_name = tool_call["function"]["name"]
                    func_args = tool_call["function"]["arguments"]

                    print(f"  -> tool call: {func_name}({func_args})")

                    # Call the tool on the MCP server
                    debug_jsonrpc("-> sent", "tools/call", {
                        "method": "tools/call",
                        "params": {"name": func_name, "arguments": func_args},
                    })
                    result = await session.call_tool(func_name, func_args)

                    # Take the search results
                    search_result = result.content[0].text if result.content else ""
                    debug_jsonrpc("<- received", "tools/call", {
                        "content": [{"type": "text", "text": search_result}],
                    })
                    print("  -> got the search results")

                    # Hand the results back to the LLM as context
                    print("  -> asking the LLM to answer from them...")
                    answer = generate_answer(context=search_result, question=user_input)

                    # Show the answer
                    print()
                    print("[Answer]")
                    print(answer)
                else:
                    # No tool call, so just show what it said
                    content = response.get("message", {}).get("content", "")
                    print()
                    print("[Answer]")
                    print(content)

                print()


def main() -> None:
    """Entry point for the rag-client command."""
    asyncio.run(run_client())


if __name__ == "__main__":
    main()
