# client/main.py — MCP クライアント

対応ソース: `src/client/main.py`（281行）

## 概要

MCP サーバーに接続し、LLM（Ollama or モック）と連携してユーザーと対話するクライアントです。

## アルゴリズム

1. MCP サーバーを子プロセスとして起動し、stdio で接続
2. `initialize` → `tools/list` でツール一覧を取得
3. ユーザーの質問を LLM に送信（ツール一覧も一緒に渡す）
4. LLM が `tool_call` を返したら → MCP サーバーでツール実行 → 結果を元に回答生成
5. LLM がテキストを返したら → そのまま表示

## 定数リファレンス

### `USE_OLLAMA`

```python
USE_OLLAMA = os.environ.get("USE_OLLAMA", "").lower() in ("1", "true", "yes")
```

環境変数 `USE_OLLAMA=1` があれば Ollama を使い、なければモック LLM を使います。

### `DEBUG`

```python
DEBUG = os.environ.get("RAG_DEBUG", "").lower() in ("1", "true", "yes")
```

`RAG_DEBUG=1` でデバッグモードを有効化します。JSON-RPC 通信の内容表示や `<think>` タグの保持に使用します。

## 関数リファレンス

### `debug_jsonrpc(direction, method, data)`

```python
def debug_jsonrpc(direction: str, method: str, data: dict) -> None
```

| 引数 | 型 | 説明 |
|------|-----|------|
| `direction` | `str` | `"→ 送信"` or `"← 受信"` |
| `method` | `str` | JSON-RPC メソッド名 |
| `data` | `dict` | 表示するデータ |

**戻り値:** なし

JSON-RPC の通信内容を整形表示します（DEBUG モード時のみ）。長いテキストは200文字で切り詰めます。

---

### `strip_think_tags(text)`

```python
def strip_think_tags(text: str) -> str
```

| 引数 | 型 | 説明 |
|------|-----|------|
| `text` | `str` | LLM の出力テキスト |

**戻り値:** `<think>...</think>` タグを除去したテキスト（デバッグモードではそのまま返す）

qwen3 モデルが出力する思考過程タグを除去します。

---

### `mock_llm(message, tools)`

```python
def mock_llm(message: str, tools: list[dict]) -> dict
```

| 引数 | 型 | 説明 |
|------|-----|------|
| `message` | `str` | ユーザーの質問 |
| `tools` | `list[dict]` | ツール定義（未使用だが Ollama と同じインターフェースに合わせる） |

**戻り値:** `{"message": {"tool_calls": [...]}}` or `{"message": {"content": "..."}}`

Ollama なしでも動作確認できるよう、キーワードマッチで「ツールを使うかどうか」を判定するモック関数です。入力に `"大堀"` `"野球"` などのキーワードが含まれていれば `tool_call` を返し、含まれていなければテキスト応答を返します。

---

### `mock_generate(context, question)`

```python
def mock_generate(context: str, question: str) -> str
```

| 引数 | 型 | 説明 |
|------|-----|------|
| `context` | `str` | 検索結果テキスト |
| `question` | `str` | ユーザーの質問 |

**戻り値:** モック回答テキスト

モック LLM 用の回答生成関数です。検索結果の先頭200文字を含む簡易回答を返します。

---

### `ollama_llm(message, tools)`

```python
def ollama_llm(message: str, tools: list[dict]) -> dict
```

| 引数 | 型 | 説明 |
|------|-----|------|
| `message` | `str` | ユーザーの質問 |
| `tools` | `list[dict]` | Ollama 形式のツール定義 |

**戻り値:** Ollama の応答（`tool_calls` を含む場合あり）

Ollama の `chat` API にユーザーメッセージと**ツール定義**を一緒に渡します。Ollama は質問の内容とツールの説明を見て、ツールを使うべきかどうかを判断し、使う場合は `tool_calls` を応答に含めます。

---

### `ollama_generate(context, question)`

```python
def ollama_generate(context: str, question: str) -> str
```

| 引数 | 型 | 説明 |
|------|-----|------|
| `context` | `str` | 検索結果テキスト |
| `question` | `str` | ユーザーの質問 |

**戻り値:** LLM が生成した回答テキスト

検索結果（context）と元の質問を組み合わせてプロンプトを構築し、LLM に回答を生成させます。ここでは `tools` を渡しません（回答生成にツール呼び出しは不要なため）。

---

### `call_llm(message, tools)`

```python
def call_llm(message: str, tools: list[dict]) -> dict
```

| 引数 | 型 | 説明 |
|------|-----|------|
| `message` | `str` | ユーザーの質問 |
| `tools` | `list[dict]` | ツール定義 |

**戻り値:** LLM の応答

`USE_OLLAMA` フラグに応じて `ollama_llm` または `mock_llm` を呼び出すディスパッチ関数です。

---

### `generate_answer(context, question)`

```python
def generate_answer(context: str, question: str) -> str
```

| 引数 | 型 | 説明 |
|------|-----|------|
| `context` | `str` | 検索結果テキスト |
| `question` | `str` | ユーザーの質問 |

**戻り値:** 回答テキスト

`USE_OLLAMA` フラグに応じて `ollama_generate` または `mock_generate` を呼び出すディスパッチ関数です。

---

### `mcp_tools_to_ollama_format(mcp_tools)`

```python
def mcp_tools_to_ollama_format(mcp_tools: list) -> list[dict]
```

| 引数 | 型 | 説明 |
|------|-----|------|
| `mcp_tools` | `list` | MCP サーバーから取得した Tool オブジェクトのリスト |

**戻り値:** Ollama 形式のツール定義リスト

MCP サーバーから取得したツール定義を Ollama が理解できる形式に変換します。

```
MCP 形式:       Tool(name="search", description="...", inputSchema={...})
  ↓ 変換
Ollama 形式:    {"type": "function", "function": {"name": "search", ...}}
```

---

### `run_client()`

```python
async def run_client()
```

**戻り値:** なし

最も重要な関数です。全体の流れ:

**1. MCP サーバーに接続:**
```python
server_params = StdioServerParameters(
    command="uv",
    args=["run", "python", "-m", "server.main"],
    env={"PYTHONPATH": "src", **os.environ},
)

async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
```

`StdioServerParameters` でサーバーの起動コマンドを指定します。
`stdio_client()` がサーバーを子プロセスとして起動し、stdin/stdout で接続します。

**2. 初期化とツール取得:**
```python
init_result = await session.initialize()  # initialize を送る
tools_result = await session.list_tools() # tools/list を送る
mcp_tools = tools_result.tools
ollama_tools = mcp_tools_to_ollama_format(mcp_tools)
```

JSON-RPC の `initialize` と `tools/list` を送り、サーバーが提供するツール一覧を取得します。

**3. 対話ループ:**
```python
while True:
    user_input = input("質問: ").strip()

    # LLM に質問（ツール一覧も一緒に渡す）
    response = call_llm(user_input, tools=ollama_tools)
    tool_calls = response.get("message", {}).get("tool_calls", [])
```

ユーザーの質問を LLM に送ります。ここでツール一覧も一緒に渡します。

**4a. ツール呼び出しがある場合:**
```python
if tool_calls:
    tool_call = tool_calls[0]
    func_name = tool_call["function"]["name"]      # "search"
    func_args = tool_call["function"]["arguments"]  # {"query": "..."}

    # MCP サーバーのツールを呼び出す（tools/call を送る）
    result = await session.call_tool(func_name, func_args)
    search_result = result.content[0].text

    # 検索結果を元に LLM で回答を生成
    answer = generate_answer(context=search_result, question=user_input)
```

LLM が tool_call を返したら、MCP サーバーにツール実行を依頼し、その結果を元に回答を生成します。

**4b. ツール呼び出しがない場合:**
```python
else:
    content = strip_think_tags(response.get("message", {}).get("content", ""))
    print(content)
```

LLM が直接テキストを返した場合は、そのまま表示します。
