"""
MCPクライアントのテスト

クライアントの各関数をテストする。
実際のMCP通信はtest_mcp_server.pyでカバー済み。
"""

from client.main import mock_llm, call_llm, mcp_tools_to_ollama_format


# テスト用のダミーツール定義（Ollama形式）
DUMMY_TOOL = {
    "type": "function",
    "function": {
        "name": "search",
        "description": "テスト用",
        "parameters": {"type": "object", "properties": {}}
    }
}


class TestMockLLM:
    """クライアント内蔵のモックLLMテスト"""

    def test_search_keyword_returns_tool_call(self):
        """検索キーワード → ツール呼び出し"""
        response = mock_llm("大堀翔の成績を教えて", tools=[DUMMY_TOOL])

        tool_calls = response["message"].get("tool_calls", [])
        assert len(tool_calls) == 1
        assert tool_calls[0]["function"]["name"] == "search"

    def test_no_keyword_returns_text(self):
        """検索キーワードなし → テキスト応答"""
        response = mock_llm("今日の天気は？", tools=[DUMMY_TOOL])

        tool_calls = response["message"].get("tool_calls", [])
        assert len(tool_calls) == 0
        assert "content" in response["message"]


class TestCallLLM:
    """call_llm関数のテスト（モックモード）"""

    def test_call_llm_uses_mock_by_default(self):
        """デフォルトではモックLLMを使用"""
        response = call_llm("大堀翔について", tools=[DUMMY_TOOL])

        tool_calls = response["message"].get("tool_calls", [])
        assert len(tool_calls) == 1


class TestToolConversion:
    """MCPツール → Ollama形式変換のテスト"""

    def test_mcp_to_ollama_format(self):
        """MCPツールがOllama形式に変換されること"""
        # MCPのToolオブジェクトをシミュレート（名前付きタプル風）
        class MockMCPTool:
            name = "search"
            description = "ChromaDBから検索"
            inputSchema = {"type": "object", "properties": {"query": {"type": "string"}}}

        mcp_tools = [MockMCPTool()]
        ollama_tools = mcp_tools_to_ollama_format(mcp_tools)

        assert len(ollama_tools) == 1
        assert ollama_tools[0]["type"] == "function"
        assert ollama_tools[0]["function"]["name"] == "search"
        assert ollama_tools[0]["function"]["description"] == "ChromaDBから検索"
