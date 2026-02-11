"""
MCPクライアント

MCPサーバーに接続し、LLM（Ollama or モック）と連携してユーザーと対話する。

使い方:
  # モックLLMで動作確認（Ollama不要）
  PYTHONPATH=src uv run python -m client.main

  # Ollamaを使う場合
  PYTHONPATH=src USE_OLLAMA=1 uv run python -m client.main
"""

import re
import sys
import os
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from server.config import CONFIG

# Ollamaを使うかモックを使うか
USE_OLLAMA = os.environ.get("USE_OLLAMA", "").lower() in ("1", "true", "yes")

# デバッグモード（<think>タグの表示に使用）
DEBUG = os.environ.get("RAG_DEBUG", "").lower() in ("1", "true", "yes")


def strip_think_tags(text: str) -> str:
    """qwen3の<think>...</think>タグを除去する。デバッグモードではそのまま返す。"""
    if DEBUG:
        return text
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


# =============================================================================
# LLM関数（モック or Ollama）
# =============================================================================

def mock_llm(message: str, tools: list[dict]) -> dict:
    """モックLLM: 検索キーワードがあればツール呼び出しを返す"""
    search_keywords = ["大堀", "野球", "成績", "投手", "打者", "二刀流", "甲子園", "メジャー", "トレーニング", "インタビュー"]

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

    return {"message": {"content": "すみません、その質問にはお答えできません。大堀翔選手について聞いてください。"}}


def mock_generate(context: str, question: str) -> str:
    """モックLLM: コンテキストを元に回答を生成（簡易版）"""
    # モックなので簡易的な回答を返す
    # 実際のOllamaでは、コンテキストを元に適切な回答が生成される
    return f"【モック回答】検索結果を元にお答えします。\n\n{context[:200]}...\n\n（実際のOllamaではより自然な回答が生成されます）"


def ollama_llm(message: str, tools: list[dict]) -> dict:
    """Ollama LLM: 実際のLLMを呼び出す"""
    import ollama
    response = ollama.chat(
        model=CONFIG["ollama_model"],
        messages=[{"role": "user", "content": message}],
        tools=tools,
    )
    return response


def ollama_generate(context: str, question: str) -> str:
    """Ollama LLM: コンテキストを元に回答を生成"""
    import ollama
    prompt = f"""以下の情報を参考にして、質問に答えてください。

【参考情報】
{context}

【質問】
{question}

【回答】"""

    response = ollama.chat(
        model=CONFIG["ollama_model"],
        messages=[{"role": "user", "content": prompt}],
    )
    return strip_think_tags(response["message"]["content"])


def call_llm(message: str, tools: list[dict]) -> dict:
    """LLMを呼び出す（ツール判定用）"""
    if USE_OLLAMA:
        return ollama_llm(message, tools)
    else:
        return mock_llm(message, tools)


def generate_answer(context: str, question: str) -> str:
    """LLMで回答を生成する（検索結果を元に）"""
    if USE_OLLAMA:
        return ollama_generate(context, question)
    else:
        return mock_generate(context, question)


# =============================================================================
# MCPツール → Ollama形式への変換
# =============================================================================

def mcp_tools_to_ollama_format(mcp_tools: list) -> list[dict]:
    """
    MCPサーバーから取得したツール一覧をOllama形式に変換する。

    MCP形式:
        Tool(name="search", description="...", inputSchema={...})

    Ollama形式:
        {"type": "function", "function": {"name": "search", "description": "...", "parameters": {...}}}
    """
    ollama_tools = []
    for tool in mcp_tools:
        ollama_tools.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.inputSchema,
            }
        })
    return ollama_tools


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
            print("[1] MCPサーバーに接続しました")

            # ツール一覧を取得（MCP の tools/list）
            tools_result = await session.list_tools()
            mcp_tools = tools_result.tools
            print(f"[2] MCPサーバーからツール一覧を取得: {[t.name for t in mcp_tools]}")

            # Ollama形式に変換（LLMに渡すため）
            ollama_tools = mcp_tools_to_ollama_format(mcp_tools)
            print(f"[3] ツール定義をLLM用の形式に変換しました")
            print()
            print("※ 以降、毎回の質問でLLMにツール一覧を渡します")
            print()

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

                # LLMに質問（ツール一覧も一緒に渡す）
                print("  → LLMに質問とツール一覧を送信...")
                response = call_llm(user_input, tools=ollama_tools)

                # LLMの判断: ツールを使うか、直接回答するか
                tool_calls = response.get("message", {}).get("tool_calls", [])

                if tool_calls:
                    # ツール呼び出しあり → MCPサーバーで検索
                    tool_call = tool_calls[0]
                    func_name = tool_call["function"]["name"]
                    func_args = tool_call["function"]["arguments"]

                    print(f"  → ツール呼び出し: {func_name}({func_args})")

                    # MCPサーバーのツールを呼び出す
                    result = await session.call_tool(func_name, func_args)

                    # 検索結果を取得
                    search_result = result.content[0].text if result.content else ""
                    print(f"  → 検索結果を取得しました")

                    # 検索結果をコンテキストとしてLLMに渡し、回答を生成
                    print(f"  → LLMに検索結果を渡して回答を生成中...")
                    answer = generate_answer(context=search_result, question=user_input)

                    # 回答を表示
                    print()
                    print("【回答】")
                    print(answer)
                else:
                    # ツール呼び出しなし → LLMの応答を表示（<think>タグは除去）
                    content = strip_think_tags(response.get("message", {}).get("content", ""))
                    print()
                    print("【回答】")
                    print(content)

                print()


if __name__ == "__main__":
    asyncio.run(run_client())
