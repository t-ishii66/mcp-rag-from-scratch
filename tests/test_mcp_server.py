"""
Tests for the MCP server

They call the registered tools directly, without starting the server.
The documents being searched are about the fictional cafe "The Wandering Kettle".
"""

from server.main import mcp


class TestSearchTool:
    """Tests for the search tool"""

    async def test_search_returns_results(self):
        """A search query returns results"""
        # In SDK v2 call_tool returns a CallToolResult (in v1 it was a tuple)
        result = await mcp.call_tool("search", {"query": "opening hours", "top_k": 3})

        assert result.content
        text = result.content[0].text
        assert "source:" in text

    async def test_search_finds_the_right_file(self):
        """Asking about opening hours returns hours_access.txt as the source"""
        result = await mcp.call_tool("search", {"query": "What time do you close?", "top_k": 3})

        text = result.content[0].text
        assert "hours_access.txt" in text

    async def test_search_matches_on_meaning(self):
        """The query words need not appear in the file"""
        result = await mcp.call_tool("search", {"query": "Can I bring my pet?", "top_k": 3})

        text = result.content[0].text
        assert "faq.txt" in text

    async def test_search_default_top_k(self):
        """Leaving out top_k still works, using the default value"""
        result = await mcp.call_tool("search", {"query": "coffee"})

        assert result.content
        assert len(result.content[0].text) > 0

    async def test_search_no_results(self):
        """An unrelated query does not raise an error"""
        result = await mcp.call_tool("search", {"query": "nonexistent keyword xyz123"})

        # This is a vector search, so there is never a "no match" case: something always comes back
        assert result.content


class TestToolDefinition:
    """Tests for the tool definition"""

    async def test_list_tools(self):
        """The search tool is registered"""
        tools = await mcp.list_tools()

        tool_names = [t.name for t in tools]
        assert "search" in tool_names

    async def test_search_tool_has_description(self):
        """The search tool has a description (the LLM reads it to decide whether to use the tool)"""
        tools = await mcp.list_tools()
        search_tool = next(t for t in tools if t.name == "search")

        assert search_tool.description is not None
        assert "search" in search_tool.description.lower()

    async def test_search_tool_input_schema(self):
        """The parameter definition contains query"""
        tools = await mcp.list_tools()
        search_tool = next(t for t in tools if t.name == "search")

        # In SDK v2 the attribute was renamed from inputSchema to input_schema.
        # The JSON that goes over the wire is still inputSchema, as the spec requires.
        assert "query" in search_tool.input_schema.get("properties", {})
