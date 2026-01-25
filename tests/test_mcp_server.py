"""
MCPサーバーのテスト

FastMCPの call_tool() を使って、サーバーを起動せずにツールをテストする。
"""

import pytest
from server.main import mcp


class TestSearchTool:
    """searchツールのテスト"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """各テスト前にChromaDBのインデックスが存在することを前提とする"""
        # インデックスは事前に作成済み（uv run python -m server.indexer）
        pass

    async def test_search_returns_results(self):
        """検索クエリに対して結果が返ること"""
        # call_tool は (contents, result_dict) のタプルを返す
        contents, _ = await mcp.call_tool("search", {"query": "野球", "top_k": 3})

        # 結果が返ること
        assert contents is not None
        assert len(contents) > 0

        # TextContentの中身を確認
        text = contents[0].text
        assert "出典:" in text

    async def test_search_default_top_k(self):
        """top_kを省略してもデフォルト値で動作すること"""
        contents, _ = await mcp.call_tool("search", {"query": "ルール"})

        assert contents is not None
        text = contents[0].text
        assert len(text) > 0

    async def test_search_no_results(self):
        """該当なしの場合もエラーにならないこと"""
        contents, _ = await mcp.call_tool("search", {"query": "存在しないキーワードxyz123"})

        # 結果が返ること（空でも可）
        assert contents is not None


class TestToolDefinition:
    """ツール定義のテスト"""

    async def test_list_tools(self):
        """searchツールが登録されていること"""
        tools = await mcp.list_tools()

        # ツールが1つ以上あること
        assert len(tools) >= 1

        # searchツールがあること
        tool_names = [t.name for t in tools]
        assert "search" in tool_names

    async def test_search_tool_has_description(self):
        """searchツールに説明があること"""
        tools = await mcp.list_tools()
        search_tool = next(t for t in tools if t.name == "search")

        assert search_tool.description is not None
        assert "検索" in search_tool.description or "ChromaDB" in search_tool.description
