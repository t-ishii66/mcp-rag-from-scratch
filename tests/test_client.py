"""
Tests for the MCP client

They test each function of the client on its own.
The real MCP communication is already covered by test_mcp_server.py.
"""

from client.main import mcp_tools_to_ollama_format


class TestToolConversion:
    """Tests for converting MCP tools into the Ollama format"""

    def test_mcp_to_ollama_format(self):
        """An MCP tool is converted into the Ollama format"""
        # Simulate an MCP Tool object (like a named tuple)
        class MockMCPTool:
            name = "search"
            description = "Search ChromaDB"
            # In SDK v2 this was renamed from inputSchema to input_schema
            input_schema = {"type": "object", "properties": {"query": {"type": "string"}}}

        mcp_tools = [MockMCPTool()]
        ollama_tools = mcp_tools_to_ollama_format(mcp_tools)

        assert len(ollama_tools) == 1
        assert ollama_tools[0]["type"] == "function"
        assert ollama_tools[0]["function"]["name"] == "search"
        assert ollama_tools[0]["function"]["description"] == "Search ChromaDB"
