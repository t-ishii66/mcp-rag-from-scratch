"""
MCPクライアント

MCPサーバーに接続し、LLM（Ollama or モック）と連携してユーザーと対話する。

使い方:
  # モックLLMで動作確認（Ollama不要）
  PYTHONPATH=src uv run python -m client.main

  # Ollamaを使う場合
  PYTHONPATH=src USE_OLLAMA=1 uv run python -m client.main
"""

import sys
import os
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Ollamaを使うかモックを使うか
USE_OLLAMA = os.environ.get("USE_OLLAMA", "").lower() in ("1", "true", "yes")


# =============================================================================
# LLM関数（モック or Ollama）
# =============================================================================

def mock_llm(message: str, tools: list[dict]) -> dict:
    """モックLLM: 検索キーワードがあればツール呼び出しを返す"""
    search_keywords = ["大谷", "野球", "ルール", "選手", "ポジション", "甲子園"]

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

    return {"message": {"content": "すみません、その質問にはお答えできません。野球について聞いてください。"}}


def ollama_llm(message: str, tools: list[dict]) -> dict:
    """Ollama LLM: 実際のLLMを呼び出す"""
    import ollama
    response = ollama.chat(
        model=os.environ.get("OLLAMA_MODEL", "qwen2.5:latest"),
        messages=[{"role": "user", "content": message}],
        tools=tools,
    )
    return response


def call_llm(message: str, tools: list[dict]) -> dict:
    """LLMを呼び出す（環境変数で切り替え）"""
    if USE_OLLAMA:
        return ollama_llm(message, tools)
    else:
        return mock_llm(message, tools)


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
                "query": {"type": "string", "description": "検索クエリ"},
                "top_k": {"type": "integer", "description": "返す結果数", "default": 5}
            },
            "required": ["query"]
        }
    }
}


# =============================================================================
# メイン処理
# =============================================================================

async def run_client():
    """MCPクライアントのメイン処理"""

    # MCPサーバーの起動コマンド
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "-m", "server.main"],
        env={"PYTHONPATH": "src", **os.environ},
    )

    print("=== MCP RAG クライアント ===")
    print(f"LLMモード: {'Ollama' if USE_OLLAMA else 'モック'}")
    print("終了するには 'quit' と入力してください")
    print()

    # MCPサーバーに接続
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # サーバー初期化
            await session.initialize()
            print("MCPサーバーに接続しました")
            print()
            #ここで MCPサーバからtools/機能一覧を取得しても良い。あくまで手順を示し、実際にsearch というものを取得する。
            # 対話ループ
            while True:
                # ユーザー入力
                try:
                    user_input = input("質問: ").strip()
                except EOFError:
                    break

                if not user_input:
                    continue
                if user_input.lower() == "quit":
                    print("終了します")
                    break

                # 1. LLMに質問（ツール呼び出しが必要か判定）
                print("  → LLMに問い合わせ中...")
                response = call_llm(user_input, tools=[SEARCH_TOOL])

                # 2. ツール呼び出しがあるか確認
                tool_calls = response.get("message", {}).get("tool_calls", [])

                if tool_calls:
                    # ツール呼び出しあり → MCPサーバーで検索
                    tool_call = tool_calls[0]
                    func_name = tool_call["function"]["name"]
                    func_args = tool_call["function"]["arguments"]

                    print(f"  → ツール呼び出し: {func_name}({func_args})")

                    # MCPサーバーのツールを呼び出す
                    result = await session.call_tool(func_name, func_args)

                    # 結果を表示
                    print()
                    print("【検索結果】")
                    for content in result.content:
                        print(content.text)
                else:
                    # ツール呼び出しなし → LLMの応答をそのまま表示
                    content = response.get("message", {}).get("content", "")
                    print()
                    print("【回答】")
                    print(content)

                print()


if __name__ == "__main__":
    asyncio.run(run_client())
