"""
Step 3: The same four exchanges, written with the official SDK

Step 2 wrote the JSON by hand. This does the same thing through the SDK, so
you can see what it takes care of.

    uv run python steps/03_mcp_sdk.py

The SDK handles the subprocess, the JSON, the ids, and the notification.
What is left is three calls:

    session.initialize()
    session.list_tools()
    session.call_tool(name, arguments)
"""

import asyncio
import os
import subprocess

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# How to start the server. The SDK spawns it for us.
SERVER = StdioServerParameters(
    command="uv",
    args=["run", "python", "-m", "server.main"],
    env=dict(os.environ),
)


async def main() -> None:
    print("=" * 72)
    print("Step 3: The same four exchanges, with the SDK")
    print("=" * 72)

    # The server logs to stderr. Drop it here so the output stays readable.
    async with stdio_client(SERVER, errlog=subprocess.DEVNULL) as (read, write):
        async with ClientSession(read, write) as session:

            # =================================================================
            # [1] initialize
            #
            # One call covers both the initialize request and the
            # notifications/initialized that follows it.
            # =================================================================
            print("\n[1] session.initialize()")
            info = await session.initialize()
            print(f"    server   : {info.server_info.name}")
            print(f"    version  : {info.protocol_version}")

            # =================================================================
            # [2] tools/list
            #
            # The tools come back as objects, not as a dict to index into.
            # =================================================================
            print("\n[2] session.list_tools()")
            tools = (await session.list_tools()).tools
            for tool in tools:
                print(f"    name     : {tool.name}")
                print(f"    arguments: {list(tool.input_schema['properties'])}")
                print(f"    required : {tool.input_schema.get('required', [])}")

            # =================================================================
            # [3] tools/call
            #
            # The arguments go in as a plain dict. The result comes back as a
            # CallToolResult, whose content is a list of typed blocks.
            # =================================================================
            print("\n[3] session.call_tool()")
            result = await session.call_tool("search", {"query": "can I bring a dog", "top_k": 1})
            text = result.content[0].text
            print(f"    is_error : {result.is_error}")
            print(f"    content  : {len(result.content)} block(s), type {result.content[0].type}")
            print(f"    text     : {len(text)} characters")
            print(f"    first    : {text.splitlines()[0]}")

    # Leaving the two async with blocks closes the connection and stops the
    # server. There is nothing to shut down by hand.
    print("\n" + "=" * 72)
    print("Three calls, and the connection closes on its own.")
    print("=" * 72)


if __name__ == "__main__":
    asyncio.run(main())
