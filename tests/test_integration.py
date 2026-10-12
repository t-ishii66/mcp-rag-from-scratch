"""
Integration tests

They test the whole flow:
  1. Connect to the MCP server (started as a separate process)
  2. Get the list of tools
  3. Stand in for the LLM and decide to call a tool
  4. Run the search on the MCP server
  5. Get the result back
"""

import os

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from client.main import mcp_tools_to_ollama_format


class TestIntegration:
    """Integration test: MCP client -> MCP server -> ChromaDB"""

    @pytest.fixture
    def server_params(self):
        """Startup parameters for the MCP server"""
        return StdioServerParameters(
            command="uv",
            args=["run", "python", "-m", "server.main"],
            env=dict(os.environ),
        )

    async def test_full_flow_with_tool_call(self, server_params):
        """
        Whole flow: a question about the cafe -> a tool call -> search results

        Steps:
          1. Connect to the MCP server
          2. Get the list of tools
          3. Stand in for the LLM (it returns a tool call)
          4. Search on the MCP server
          5. Check the result
        """
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                tools_result = await session.list_tools()
                mcp_tools = tools_result.tools
                assert "search" in [t.name for t in mcp_tools]

                # The definitions reach the LLM in this shape
                ollama_tools = mcp_tools_to_ollama_format(mcp_tools)
                assert ollama_tools[0]["function"]["name"] == "search"

                # Stand in for the LLM: this is what it answers with
                tool_call = {"name": "search", "arguments": {"query": "opening hours"}}

                # Run it on the MCP server, exactly as the client does
                result = await session.call_tool(tool_call["name"], tool_call["arguments"])

                assert result.content
                assert "source:" in result.content[0].text

    async def test_search_returns_relevant_results(self, server_params):
        """The search results are relevant to the question"""
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.call_tool(
                    "search", {"query": "Do you have oat milk?", "top_k": 3}
                )

                text = result.content[0].text
                # The allergens and dietary restrictions document should be found
                assert "allergens.txt" in text
