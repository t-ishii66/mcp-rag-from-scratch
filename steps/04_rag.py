"""
Step 4: RAG

The LLM arrives here. Everything before this was the retrieval half; this
adds the model that reads what came back and writes the answer.

    uv run python steps/04_rag.py

Ollama is called twice, and the two calls want different things:

    1. question + tool definitions  ->  "call search with these arguments"
    2. question + search results     ->  the answer

The LLM never runs anything. It asks for a tool, and this script makes the
call over MCP.
"""

import asyncio
import os
import subprocess

import ollama
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:1.7b")

SERVER = StdioServerParameters(
    command="uv",
    args=["run", "python", "-m", "server.main"],
    env=dict(os.environ),
)

QUESTION = "Can I bring my dog to the cafe?"


def to_ollama_format(tools: list) -> list[dict]:
    """Repack the MCP tool definitions into the shape Ollama expects."""
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.input_schema,
            },
        }
        for tool in tools
    ]


async def main() -> None:
    print("=" * 72)
    print("Step 4: RAG")
    print("=" * 72)
    print(f"\nQuestion: {QUESTION}")

    async with stdio_client(SERVER, errlog=subprocess.DEVNULL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # =================================================================
            # [1] Ask the server what it offers, and repack it for Ollama
            # =================================================================
            tools = (await session.list_tools()).tools
            ollama_tools = to_ollama_format(tools)
            print(f"\n[1] tools from the server: {[t.name for t in tools]}")

            # =================================================================
            # [2] First call: hand the question and the tools to the LLM
            #
            # What comes back is a request to call a tool, not a result.
            # =================================================================
            print("\n[2] asking the LLM what to do")
            # Thinking is left on. qwen3:1.7b picks the tool far more reliably
            # when it is allowed to reason first.
            decision = ollama.chat(
                model=MODEL,
                messages=[{"role": "user", "content": QUESTION}],
                tools=ollama_tools,
            )

            # ollama returns objects, not dicts. message.tool_calls is None
            # when the model chose to answer instead of calling anything.
            calls = decision.message.tool_calls
            if not calls:
                print("    the LLM answered without the tool:")
                print(f"    {decision.message.content}")
                return

            name = calls[0].function.name
            arguments = calls[0].function.arguments
            print(f"    it asked for: {name}({arguments})")

            # =================================================================
            # [3] Run the tool over MCP
            # =================================================================
            print("\n[3] calling the tool through the MCP server")
            result = await session.call_tool(name, arguments)
            passages = result.content[0].text
            print(f"    got {len(passages)} characters back")

            # =================================================================
            # [4] Second call: hand the question and the passages to the LLM
            # =================================================================
            print("\n[4] asking the LLM to answer from them")
            prompt = (
                "Answer the question using only the reference material below.\n\n"
                f"[Reference]\n{passages}\n\n"
                f"[Question]\n{QUESTION}\n\n"
                "[Answer]"
            )
            answer = ollama.chat(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                think=False,
            )

    print("\n" + "=" * 72)
    print("Answer")
    print("=" * 72)
    print(answer.message.content.strip())


if __name__ == "__main__":
    asyncio.run(main())
