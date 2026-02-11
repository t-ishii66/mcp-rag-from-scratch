"""
Ollama tool calling のテスト

開発中はOllamaを使わず、モックLLM関数で動作確認する。
本番ではこのモックをOllamaに差し替える。
"""


# =============================================================================
# モックLLM関数
# =============================================================================

def mock_llm(message: str, tools: list[dict]) -> dict:
    """
    モックLLM関数。入力パターンに応じて固定の応答を返す。

    Args:
        message: ユーザーのメッセージ
        tools: 利用可能なツール定義のリスト

    Returns:
        LLMの応答（tool_callsがあればツール呼び出し、なければテキスト応答）

    応答の形式（Ollama互換）:
        ツール呼び出しあり:
            {"message": {"tool_calls": [{"function": {"name": "search", "arguments": {"query": "..."}}}]}}
        テキスト応答:
            {"message": {"content": "こんにちは！"}}
    """
    # パターン1: 検索が必要なキーワードを含む → ツール呼び出し
    search_keywords = ["大堀", "野球", "ルール", "選手", "ポジション", "甲子園"]

    for keyword in search_keywords:
        if keyword in message:
            return {
                "message": {
                    "tool_calls": [{
                        "function": {
                            "name": "search",
                            "arguments": {"query": message}
                        }
                    }]
                }
            }

    # パターン2: 挨拶など → テキスト応答（ツール呼び出しなし）
    return {
        "message": {
            "content": "こんにちは！何かお手伝いしましょうか？"
        }
    }


def has_tool_calls(response: dict) -> bool:
    """レスポンスにツール呼び出しが含まれるか判定"""
    return "tool_calls" in response.get("message", {})


def get_tool_calls(response: dict) -> list[dict]:
    """レスポンスからツール呼び出しを取り出す"""
    return response.get("message", {}).get("tool_calls", [])


def get_text_content(response: dict) -> str:
    """レスポンスからテキスト内容を取り出す"""
    return response.get("message", {}).get("content", "")


# =============================================================================
# ツール定義（Ollama形式）
# =============================================================================

SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "search",
        "description": "ChromaDBから関連テキストを検索する",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "検索クエリ"
                },
                "top_k": {
                    "type": "integer",
                    "description": "返す結果数",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    }
}


# =============================================================================
# テスト
# =============================================================================

class TestMockLLM:
    """モックLLMの動作テスト"""

    def test_search_keyword_triggers_tool_call(self):
        """検索キーワードを含む質問 → ツール呼び出し"""
        response = mock_llm("大堀翔について教えて", tools=[SEARCH_TOOL])

        # ツール呼び出しがあること
        assert has_tool_calls(response)

        # searchツールが呼ばれること
        tool_calls = get_tool_calls(response)
        assert tool_calls[0]["function"]["name"] == "search"

    def test_greeting_returns_text(self):
        """挨拶 → テキスト応答（ツール呼び出しなし）"""
        response = mock_llm("こんにちは", tools=[SEARCH_TOOL])

        # ツール呼び出しがないこと
        assert not has_tool_calls(response)

        # テキスト応答があること
        text = get_text_content(response)
        assert len(text) > 0

    def test_baseball_question_triggers_tool_call(self):
        """野球に関する質問 → ツール呼び出し"""
        response = mock_llm("野球のルールを教えて", tools=[SEARCH_TOOL])

        assert has_tool_calls(response)
        tool_calls = get_tool_calls(response)
        assert "野球" in tool_calls[0]["function"]["arguments"]["query"]


class TestToolDefinition:
    """ツール定義のフォーマットテスト"""

    def test_tool_has_required_fields(self):
        """ツール定義に必要なフィールドがあること"""
        assert SEARCH_TOOL["type"] == "function"
        assert "name" in SEARCH_TOOL["function"]
        assert "description" in SEARCH_TOOL["function"]
        assert "parameters" in SEARCH_TOOL["function"]

    def test_parameters_has_query(self):
        """パラメータにqueryがあること"""
        params = SEARCH_TOOL["function"]["parameters"]
        assert "query" in params["properties"]
        assert "query" in params["required"]
