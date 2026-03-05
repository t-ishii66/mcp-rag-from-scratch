# MCP プロトコル解説

## MCP とは何か

**MCP（Model Context Protocol）** は、LLM（大規模言語モデル）に外部ツールを使わせるための通信規格です。

LLM は単体ではテキスト生成しかできません。データベースの検索、API の呼び出し、ファイルの読み書きなど、外部とのやりとりには別の仕組みが必要です。MCP はその仕組みを標準化したプロトコルです。

### 日常の例え

レストランに例えると:

- **お客さん（ユーザー）**: 「カルボナーラをください」
- **ウェイター（LLM + MCP クライアント）**: 注文を受けて、厨房に伝える
- **厨房（MCP サーバー）**: 実際に料理を作って渡す
- **メニュー（ツール定義）**: 何を注文できるか一覧にしたもの

LLM 単体はウェイターが厨房なしで働くようなもの。MCP を使うと厨房（外部ツール）と連携できるようになります。

## MCP のアーキテクチャ

```
┌───────────────────────────────────┐
│         MCP クライアント           │
│                                   │
│  ユーザーの質問を受け取り、        │
│  LLM にツールの一覧と一緒に渡す。  │
│  LLM が「ツールを使う」と判断したら │
│  MCP サーバーにリクエストを送る。   │
└──────────┬────────────────────────┘
           │
     JSON-RPC（stdio）
           │
┌──────────▼────────────────────────┐
│         MCP サーバー               │
│                                   │
│  ツール（search など）を定義し、    │
│  クライアントからの呼び出しに応じて │
│  実際の処理を実行して結果を返す。   │
└───────────────────────────────────┘
```

### クライアントとサーバーの役割分担

| 役割 | やること | このプロジェクトでは |
|------|---------|-------------------|
| **クライアント** | LLM との対話、ツール呼び出しの判断 | `src/client/main.py` |
| **サーバー** | ツールの定義と実行 | `src/server/main.py` |

## JSON-RPC とは

MCP の通信は **JSON-RPC 2.0** で行われます。

JSON-RPC は「メソッド名」と「引数」を JSON で送り、「結果」を JSON で受け取るシンプルな仕組みです。REST API に似ていますが、HTTP ではなく **標準入出力（stdio）** を使います。

### なぜ stdio？

MCP クライアントは MCP サーバーを**子プロセス**として起動します。親プロセス（クライアント）と子プロセス（サーバー）の間で、stdin / stdout を通じて JSON をやりとりします。

```
クライアント（親プロセス）
    │
    │ stdin に JSON を書き込む → サーバーが読む
    │ stdout から JSON を読む  ← サーバーが書き込む
    │
サーバー（子プロセス）
```

この方式のメリット:

- HTTP サーバーを立てる必要がない
- ネットワーク設定が不要
- プロセスを起動するだけで通信できる

### 通信の流れ

MCP の通信は3つのステップで行われます。

#### ステップ 1: `initialize`（接続確立）

クライアントがサーバーに接続し、お互いの機能を確認します。

```
クライアント → サーバー:
{
  "jsonrpc": "2.0",
  "method": "initialize",
  "params": { "capabilities": {} }
}

サーバー → クライアント:
{
  "jsonrpc": "2.0",
  "result": {
    "serverInfo": { "name": "rag-search-server" },
    "capabilities": { "tools": {} }
  }
}
```

#### ステップ 2: `tools/list`（ツール一覧の取得）

クライアントが「どんなツールが使えますか？」とサーバーに聞きます。

```
クライアント → サーバー:
{
  "jsonrpc": "2.0",
  "method": "tools/list"
}

サーバー → クライアント:
{
  "jsonrpc": "2.0",
  "result": {
    "tools": [
      {
        "name": "search",
        "description": "架空の野球選手・大堀翔に関する情報を検索する。",
        "inputSchema": {
          "type": "object",
          "properties": {
            "query": { "type": "string" },
            "top_k": { "type": "integer", "default": 5 }
          },
          "required": ["query"]
        }
      }
    ]
  }
}
```

この情報は LLM に渡されます。LLM はツールの名前・説明・パラメータを見て、使うべきかどうかを判断します。

#### ステップ 3: `tools/call`（ツールの実行）

LLM が「このツールを使いたい」と判断したら、クライアントがサーバーにツール実行を依頼します。

```
クライアント → サーバー:
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "search",
    "arguments": { "query": "大堀翔の成績", "top_k": 3 }
  }
}

サーバー → クライアント:
{
  "jsonrpc": "2.0",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "[1] 出典: stats.txt (類似度: 0.91)\n大堀翔の詳細成績データ..."
      }
    ]
  }
}
```

## ツール呼び出しの判断は誰がする？

**LLM（Ollama）が判断します。** これが MCP の核心的なポイントです。

1. クライアントが LLM にユーザーの質問と**ツール一覧**を一緒に渡す
2. LLM が質問の内容を見て「このツールが必要だ」と判断する
3. LLM は「search ツールを query="大堀翔の成績" で呼んでほしい」という応答を返す
4. クライアントがその指示に従って MCP サーバーのツールを呼び出す

```
ユーザー: 「大堀翔の成績は？」

     ↓ 質問 + ツール一覧を送る

LLM: 「search ツールを使ってください。query は "大堀翔の成績" で。」
     （これが tool_call レスポンス）

     ↓ クライアントが MCP サーバーに中継

MCP サーバー: 「検索結果はこちらです: [1] 出典: stats.txt ...」

     ↓ 検索結果を LLM に戻す

LLM: 「大堀翔の2021年の成績は打率.310、本塁打32本です。」
```

### LLM がツールを使わないケース

質問がツールの対象外の場合、LLM はツールを使わず直接回答します。

```
ユーザー: 「こんにちは」

     ↓ 質問 + ツール一覧を送る

LLM: 「こんにちは！何かお手伝いできることはありますか？」
     （tool_call なし、テキストだけの応答）
```

## このプロジェクトでの実装

### サーバー側: ツールの定義

`src/server/main.py` では、FastMCP のデコレータでツールを定義しています:

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("rag-search-server")

@mcp.tool()
def search(query: str, top_k: int = 5) -> str:
    """架空の野球選手・大堀翔に関する情報を検索する。"""
    # ChromaDB でベクトル検索を実行
    ...
```

`@mcp.tool()` デコレータを付けるだけで:
- 関数名がツール名になる
- docstring がツールの説明になる
- 引数の型ヒントがパラメータ定義になる

### クライアント側: サーバーへの接続

`src/client/main.py` では、MCP SDK の `stdio_client` でサーバーに接続しています:

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# サーバーの起動コマンドを指定
server_params = StdioServerParameters(
    command="uv",
    args=["run", "python", "-m", "server.main"],
)

# サーバーを子プロセスとして起動し、stdio で接続
async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()               # 接続確立
        tools = await session.list_tools()        # ツール一覧取得
        result = await session.call_tool(...)     # ツール実行
```

### ツール形式の変換

MCP のツール定義と Ollama のツール定義は形式が異なるため、変換が必要です:

```python
# MCP形式（サーバーから取得）
Tool(name="search", description="...", inputSchema={...})

# Ollama形式（LLM に渡す）
{"type": "function", "function": {"name": "search", ...}}
```

この変換は `mcp_tools_to_ollama_format()` 関数が行います。

## デバッグ: 通信内容を見る

`RAG_DEBUG=1` を付けて起動すると、実際の JSON-RPC メッセージが表示されます。

```bash
RAG_DEBUG=1 PYTHONPATH=src uv run python -m client.main
```

`initialize` → `tools/list` → `tools/call` の流れが見えるので、プロトコルの理解に最適です。

## まとめ

| 概念 | 説明 |
|------|------|
| **MCP** | LLM に外部ツールを使わせる通信規格 |
| **JSON-RPC** | メソッド名と引数を JSON で送り合う仕組み |
| **stdio** | 親子プロセス間で標準入出力を使った通信 |
| **クライアント** | LLM と対話し、必要に応じてサーバーのツールを呼ぶ |
| **サーバー** | ツールを定義し、呼ばれたら実行して結果を返す |
| **ツール判定** | LLM がツール一覧を見て「使うかどうか」を自分で判断する |
