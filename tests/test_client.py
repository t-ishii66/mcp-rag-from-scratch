"""
MCPクライアントのテスト

クライアントの各関数をテストする。
実際のMCP通信はtest_mcp_server.pyでカバー済み。
"""

from client.main import mock_llm, call_llm, SEARCH_TOOL


class TestMockLLM:
    """クライアント内蔵のモックLLMテスト"""

    def test_search_keyword_returns_tool_call(self):
        """検索キーワード → ツール呼び出し"""
        response = mock_llm("野球のルールを教えて", tools=[SEARCH_TOOL])

        tool_calls = response["message"].get("tool_calls", [])
        assert len(tool_calls) == 1
        assert tool_calls[0]["function"]["name"] == "search"

    def test_no_keyword_returns_text(self):
        """検索キーワードなし → テキスト応答"""
        response = mock_llm("今日の天気は？", tools=[SEARCH_TOOL])

        tool_calls = response["message"].get("tool_calls", [])
        assert len(tool_calls) == 0
        assert "content" in response["message"]


class TestCallLLM:
    """call_llm関数のテスト（モックモード）"""

    def test_call_llm_uses_mock_by_default(self):
        """デフォルトではモックLLMを使用"""
        # USE_OLLAMA環境変数がない場合はモックを使う
        response = call_llm("大谷翔平について", tools=[SEARCH_TOOL])

        # モックの動作を確認
        tool_calls = response["message"].get("tool_calls", [])
        assert len(tool_calls) == 1


class TestToolDefinition:
    """ツール定義のテスト"""

    def test_search_tool_format(self):
        """SEARCH_TOOLがOllama形式であること"""
        assert SEARCH_TOOL["type"] == "function"
        assert SEARCH_TOOL["function"]["name"] == "search"
        assert "parameters" in SEARCH_TOOL["function"]
