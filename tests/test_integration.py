"""
統合テスト

全体フローをテストする:
  1. MCPサーバーに接続
  2. ツール一覧を取得
  3. LLM（モック）でツール呼び出し判定
  4. MCPサーバーで検索実行
  5. 結果を取得
"""

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from client.main import mock_llm, mcp_tools_to_ollama_format


class TestIntegration:
    """統合テスト: MCPクライアント → MCPサーバー → ChromaDB"""

    @pytest.fixture
    def server_params(self):
        """MCPサーバーの起動パラメータ"""
        import os
        return StdioServerParameters(
            command="uv",
            args=["run", "python", "-m", "server.main"],
            env={"PYTHONPATH": "src", **os.environ},
        )

    async def test_full_flow_with_tool_call(self, server_params):
        """
        全体フロー: 野球の質問 → ツール呼び出し → 検索結果

        手順:
          1. MCPサーバーに接続
          2. ツール一覧を取得
          3. モックLLMに質問（ツール呼び出しを返す）
          4. MCPサーバーで検索
          5. 結果を確認
        """
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # 1. サーバー初期化
                await session.initialize()

                # 2. ツール一覧を取得
                tools_result = await session.list_tools()
                mcp_tools = tools_result.tools

                # searchツールがあることを確認
                tool_names = [t.name for t in mcp_tools]
                assert "search" in tool_names

                # 3. Ollama形式に変換してモックLLMに渡す
                ollama_tools = mcp_tools_to_ollama_format(mcp_tools)
                response = mock_llm("大堀翔の成績を教えて", tools=ollama_tools)

                # ツール呼び出しがあることを確認
                tool_calls = response["message"].get("tool_calls", [])
                assert len(tool_calls) == 1
                assert tool_calls[0]["function"]["name"] == "search"

                # 4. MCPサーバーで検索実行
                func_name = tool_calls[0]["function"]["name"]
                func_args = tool_calls[0]["function"]["arguments"]
                result = await session.call_tool(func_name, func_args)

                # 5. 結果を確認
                assert result.content is not None
                assert len(result.content) > 0
                text = result.content[0].text
                assert "出典:" in text

    async def test_full_flow_without_tool_call(self, server_params):
        """
        全体フロー: 野球以外の質問 → ツール呼び出しなし

        手順:
          1. MCPサーバーに接続
          2. ツール一覧を取得
          3. モックLLMに質問（テキスト応答を返す）
          4. ツール呼び出しがないことを確認
        """
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # 1. サーバー初期化
                await session.initialize()

                # 2. ツール一覧を取得
                tools_result = await session.list_tools()
                ollama_tools = mcp_tools_to_ollama_format(tools_result.tools)

                # 3. モックLLMに質問（野球以外）
                response = mock_llm("今日の天気は？", tools=ollama_tools)

                # 4. ツール呼び出しがないことを確認
                tool_calls = response["message"].get("tool_calls", [])
                assert len(tool_calls) == 0

                # テキスト応答があることを確認
                content = response["message"].get("content", "")
                assert len(content) > 0

    async def test_search_returns_relevant_results(self, server_params):
        """検索結果が質問に関連していることを確認"""
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # 「成績」で検索
                result = await session.call_tool("search", {"query": "大堀翔の投手成績", "top_k": 3})

                text = result.content[0].text
                # 大堀翔の成績に関する内容が含まれること
                assert "大堀" in text or "投手" in text or "防御率" in text or "勝" in text
