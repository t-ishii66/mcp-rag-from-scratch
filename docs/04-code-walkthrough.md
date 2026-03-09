# コード解説

このプロジェクトの全ソースコードを解説します。
ファイルごとに処理の流れを追い、何をしているかを1つずつ説明します。

## ファイル構成

```
src/
├── server/
│   ├── config.py       ← 設定値の管理（最もシンプル）
│   ├── indexer.py      ← テキスト → ChromaDB への保存
│   └── main.py         ← MCP サーバー本体（search ツール）
└── client/
    └── main.py         ← MCP クライアント + LLM 連携
```

読む順番は `config.py` → `indexer.py` → `server/main.py` → `client/main.py` がおすすめです。

---

## 1. `src/server/config.py` — 設定管理

**38行。** 環境変数からの設定読み込みを辞書1つで管理する、最もシンプルなファイルです。

```python
PROJECT_ROOT = Path(__file__).parent.parent.parent
```

`config.py` は `src/server/config.py` にあるので、`.parent` を3回呼ぶとプロジェクトルートに到達します:

```
config.py → server/ → src/ → プロジェクトルート
  .parent    .parent   .parent
```

```python
CONFIG = {
    "documents_path": Path(os.environ.get("RAG_DOCUMENTS_PATH", PROJECT_ROOT / "data" / "documents")),
    "chroma_path": Path(os.environ.get("RAG_CHROMA_PATH", PROJECT_ROOT / "chroma_db")),
    "chunk_size": int(os.environ.get("RAG_CHUNK_SIZE", "400")),
    "chunk_overlap": int(os.environ.get("RAG_CHUNK_OVERLAP", "80")),
    "ollama_model": os.environ.get("OLLAMA_MODEL", "qwen3:1.7b"),
    "embedding_model": "intfloat/multilingual-e5-small",
}
```

パターンは全て同じ: `os.environ.get("環境変数名", "デフォルト値")`。
環境変数があればそれを使い、なければデフォルト値を使います。

`embedding_model` だけは環境変数なしの固定値です。E5 モデルは埋め込み時のプレフィックス規約があるため、気軽に変更できません。

---

## 2. `src/server/indexer.py` — インデックス作成

**158行。** テキストファイルを読み込み、チャンクに分割して ChromaDB に保存します。

### 埋め込みモデルの初期化

```python
EMBEDDING_FUNCTION = SentenceTransformerEmbeddingFunction(
    model_name=CONFIG["embedding_model"]
)
E5_DOCUMENT_PREFIX = "passage: "
```

ChromaDB に渡す埋め込み関数を作成します。`SentenceTransformerEmbeddingFunction` は ChromaDB が提供するラッパーで、テキストを渡すと自動でベクトルに変換してくれます。

`E5_DOCUMENT_PREFIX` は E5 モデルの規約で、保存する文書には `"passage: "` を付けます（詳しくは [RAG 解説](./03-rag-explained.md) を参照）。

### `load_text_files()` — ファイル読み込み

```python
def load_text_files(documents_path: Path) -> list[dict]:
    documents = []
    for txt_file in documents_path.glob("*.txt"):
        content = txt_file.read_text(encoding="utf-8")
        documents.append({"filename": txt_file.name, "content": content})
    return documents
```

指定フォルダ内の `.txt` ファイルを全て読み込み、`[{"filename": "xxx.txt", "content": "..."}]` の形で返します。`glob("*.txt")` で `.txt` ファイルだけを取得します。

### `split_into_chunks()` — チャンク分割

```python
def split_into_chunks(text: str, chunk_size: int, overlap: int) -> list[str]:
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap   # ← オーバーラップぶん戻る
    return chunks
```

テキストを `chunk_size` 文字ごとに分割します。次のチャンクの開始位置を `overlap` 文字ぶん手前に戻すことで、チャンク間に重複区間を作ります。

例: 1000文字のテキスト、chunk_size=400、overlap=80 の場合

```
チャンク1: text[0:400]
チャンク2: text[320:720]     ← 400-80=320 から開始
チャンク3: text[640:1000]    ← 720-80=640 から開始
```

### `index_documents()` — メイン処理

```python
def index_documents(documents_path, chroma_path, chunk_size, chunk_overlap, collection_name="documents"):
```

全体を統括する関数です。処理の流れ:

**ステップ 1: テキスト読み込み**
```python
documents = load_text_files(documents_path)
```

**ステップ 2: ChromaDB 初期化**
```python
client = chromadb.PersistentClient(path=str(chroma_path))

# 既存のコレクションがあれば削除して新規作成
existing = [c.name for c in client.list_collections()]
if collection_name in existing:
    client.delete_collection(collection_name)

collection = client.create_collection(name=collection_name, embedding_function=EMBEDDING_FUNCTION)
```

`PersistentClient` はデータをディスクに永続化するモードです。
既存データがあれば削除して最初から作り直します（毎回クリーンな状態にするため）。

**ステップ 3: チャンク分割と保存**
```python
for doc in documents:
    chunks = split_into_chunks(doc["content"], chunk_size, chunk_overlap)
    for i, chunk in enumerate(chunks):
        chunk_id = f"{doc['filename']}_{i}"
        collection.add(
            ids=[chunk_id],
            documents=[f"{E5_DOCUMENT_PREFIX}{chunk}"],
            metadatas=[{"source": doc["filename"], "chunk_index": i}],
        )
```

各チャンクに一意の ID（`"profile.txt_0"`, `"profile.txt_1"` など）を付けて ChromaDB に保存します。
`documents` に渡したテキストは ChromaDB が自動でベクトル化します。
`metadatas` には出典ファイル名を記録し、検索結果に「出典: profile.txt」と表示できるようにします。

---

## 3. `src/server/main.py` — MCP サーバー

**123行。** ChromaDB の検索ツールを MCP プロトコルで提供するサーバーです。

### デバッグログ

```python
DEBUG = os.environ.get("RAG_DEBUG", "").lower() in ("1", "true", "yes")

def debug_log(message: str) -> None:
    if DEBUG:
        print(f"[DEBUG] {message}", file=sys.stderr)
```

stdout は JSON-RPC 通信で使うため、デバッグログは **stderr** に出力します。
`file=sys.stderr` がポイントです。stdout に余計な出力を混ぜると JSON-RPC のパースが壊れます。

### MCP サーバーの作成

```python
mcp = FastMCP("rag-search-server")
```

FastMCP は MCP SDK が提供する簡易サーバークラスです。`"rag-search-server"` はサーバー名で、クライアントの `initialize` 応答に含まれます。

### ChromaDB の遅延初期化

```python
_collection = None

def get_collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=str(CONFIG["chroma_path"]))
        _collection = client.get_collection("documents", embedding_function=EMBEDDING_FUNCTION)
    return _collection
```

ChromaDB への接続は初回の `search()` 呼び出し時まで遅延されます。
サーバー起動時に接続すると、テストでサーバーを import しただけで ChromaDB が必要になってしまうため、この設計にしています。

`get_collection()` ではインデクサーと違い `get_collection()`（既存コレクションの取得）を使います。`create_collection()` ではありません。インデクサーで事前に作成されたコレクションを使い回します。

### `search()` ツール

```python
@mcp.tool()
def search(query: str, top_k: int = 5) -> str:
```

`@mcp.tool()` デコレータにより、この関数が MCP ツールとして登録されます。

**検索実行:**
```python
collection = get_collection()
results = collection.query(
    query_texts=[f"{E5_QUERY_PREFIX}{query}"],
    n_results=top_k,
)
```

クエリに `"query: "` プレフィックスを付けてベクトル化し、ChromaDB で類似度検索を実行します。

**結果の整形:**
```python
documents = results["documents"][0]
metadatas = results["metadatas"][0]
distances = results["distances"][0]

for i, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances)):
    source = meta.get("source", "不明")
    score = 1 - dist
    output_lines.append(f"[{i+1}] 出典: {source} (類似度: {score:.2f})")
    output_lines.append(doc)
```

ChromaDB の検索結果は `[0]` で取り出す必要があります（クエリが1つでもリストのリストで返るため）。
距離（distance）を `1 - dist` で類似度の目安スコアとして表示し、出典ファイル名と一緒に返します。
距離の定義によってはこのスコアが 0〜1 の範囲外になる場合もあります。

### サーバー起動

```python
if __name__ == "__main__":
    mcp.run()
```

`mcp.run()` は stdio 経由の JSON-RPC リスナーを起動します。stdin からリクエストを読み、stdout にレスポンスを書きます。

---

## 4. `src/client/main.py` — MCP クライアント

**281行。** MCP サーバーに接続し、LLM と連携してユーザーと対話するクライアントです。

### LLM の切り替え

```python
USE_OLLAMA = os.environ.get("USE_OLLAMA", "").lower() in ("1", "true", "yes")
```

環境変数 `USE_OLLAMA=1` があれば Ollama を使い、なければモック LLM を使います。

### モック LLM

```python
def mock_llm(message: str, tools: list[dict]) -> dict:
    search_keywords = ["大堀", "野球", "成績", "投手", "打者", ...]
    for keyword in search_keywords:
        if keyword in message:
            return {"message": {"tool_calls": [...]}}
    return {"message": {"content": "すみません、..."}}
```

Ollama なしでも動作確認できるよう、キーワードマッチで「ツールを使うかどうか」を判定するモック関数です。入力に `"大堀"` `"野球"` などのキーワードが含まれていれば tool_call を返し、含まれていなければテキスト応答を返します。

実際の Ollama LLM はこのような単純なキーワードマッチではなく、質問の意味を理解してツール呼び出しを判断します。

### Ollama LLM

```python
def ollama_llm(message: str, tools: list[dict]) -> dict:
    import ollama
    response = ollama.chat(
        model=CONFIG["ollama_model"],
        messages=[{"role": "user", "content": message}],
        tools=tools,
    )
    return response
```

Ollama の `chat` API にユーザーメッセージと**ツール定義**を一緒に渡します。Ollama は質問の内容とツールの説明を見て、ツールを使うべきかどうかを判断し、使う場合は `tool_calls` を応答に含めます。

### 回答生成

```python
def ollama_generate(context: str, question: str) -> str:
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
```

検索結果（context）と元の質問を組み合わせてプロンプトを構築し、LLM に回答を生成させます。ここでは `tools` を渡しません（回答生成にツール呼び出しは不要なため）。

`strip_think_tags()` は qwen3 モデルが出力する `<think>...</think>` タグ（思考過程）を除去する関数です。

### ツール形式の変換

```python
def mcp_tools_to_ollama_format(mcp_tools: list) -> list[dict]:
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
```

MCP サーバーから取得したツール定義を Ollama が理解できる形式に変換します。

```
MCP 形式:       Tool(name="search", description="...", inputSchema={...})
  ↓ 変換
Ollama 形式:    {"type": "function", "function": {"name": "search", ...}}
```

### メイン処理 `run_client()`

最も重要な関数です。全体の流れを順に追います。

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

---

## テストの構成

```
tests/
├── conftest.py          ← テスト前にインデックスを作成するフィクスチャ
├── test_chromadb.py     ← ChromaDB の基本操作テスト
├── test_indexer.py      ← チャンク分割・ファイル読み込みのテスト
├── test_mcp_server.py   ← MCP サーバーのツールテスト
├── test_client.py       ← クライアントロジックのテスト
├── test_ollama_tools.py ← モック LLM の動作テスト
└── test_integration.py  ← MCP サーバー起動 → 検索の統合テスト
```

### テストの特徴

- `test_mcp_server.py`: `await mcp.call_tool("search", ...)` でサーバープロセスを起動せずにツール関数を直接テストしている
- `test_integration.py`: `stdio_client` で実際にサーバーを子プロセスとして起動し、JSON-RPC 通信を含めた統合テストを行っている
- `conftest.py`: テストセッション開始時に `index_documents()` を呼び、テスト用の ChromaDB を事前に作成する

---

## 処理の全体フローまとめ

```
[ユーザー]
    │ 「大堀翔の成績は？」
    ▼
[client/main.py]
    │ call_llm(質問, ツール一覧)
    ▼
[Ollama or モック LLM]
    │ 「search ツールを使って」 (tool_call)
    ▼
[client/main.py]
    │ session.call_tool("search", {"query": "大堀翔の成績"})
    │                 ↕ JSON-RPC (stdio)
    ▼
[server/main.py]
    │ search("大堀翔の成績", top_k=5)
    │ get_collection()  ← 初回のみ ChromaDB に接続
    │ collection.query(...)  ← ベクトル検索
    │ 結果を整形して返す
    ▼
[client/main.py]
    │ generate_answer(検索結果, 元の質問)
    ▼
[Ollama or モック LLM]
    │ 検索結果を参考に回答を生成
    ▼
[ユーザー]
    「大堀翔の2021年の成績は打率.310、本塁打32本です。」
```
