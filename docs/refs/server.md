# server/main.py — MCP サーバー

対応ソース: `src/server/main.py`（122行）

## 概要

ChromaDB の検索ツールを MCP プロトコルで提供するサーバーです。JSON-RPC 2.0 で stdio 通信を行います。

## アルゴリズム

1. FastMCP でサーバーインスタンスを作成
2. `@mcp.tool()` で `search` 関数をツールとして登録
3. `mcp.run()` で stdio 経由の JSON-RPC リスナーを起動
4. クライアントから `tools/call` が来たら、ChromaDB でベクトル検索を実行して結果を返す

## 定数リファレンス

### `DEBUG`

```python
DEBUG = os.environ.get("RAG_DEBUG", "").lower() in ("1", "true", "yes")
```

`RAG_DEBUG=1` でデバッグログを有効化します。

### `mcp`

```python
mcp = FastMCP("rag-search-server")
```

FastMCP は MCP SDK が提供する簡易サーバークラスです。`"rag-search-server"` はサーバー名で、クライアントの `initialize` 応答に含まれます。

### `E5_QUERY_PREFIX`

```python
E5_QUERY_PREFIX = "query: "
```

E5 モデルの規約で、検索クエリには `"query: "` を付けます（インデクサーの `"passage: "` と対になる）。

## 関数リファレンス

### `debug_log(message)`

```python
def debug_log(message: str) -> None
```

| 引数 | 型 | 説明 |
|------|-----|------|
| `message` | `str` | ログメッセージ |

**戻り値:** なし

stdout は JSON-RPC 通信で使うため、デバッグログは **stderr** に出力します。
`file=sys.stderr` がポイントです。stdout に余計な出力を混ぜると JSON-RPC のパースが壊れます。

---

### `get_collection()`

```python
def get_collection()
```

**戻り値:** ChromaDB の Collection オブジェクト

ChromaDB への接続は初回の `search()` 呼び出し時まで遅延されます（遅延初期化パターン）。
サーバー起動時に接続すると、テストでサーバーを import しただけで ChromaDB が必要になってしまうため、この設計にしています。

```python
_collection = None

def get_collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=str(CONFIG["chroma_path"]))
        _collection = client.get_collection("documents", embedding_function=EMBEDDING_FUNCTION)
    return _collection
```

インデクサーと違い `get_collection()`（既存コレクションの取得）を使います。`create_collection()` ではありません。インデクサーで事前に作成されたコレクションを使い回します。

---

### `search(query, top_k)` — MCP ツール

```python
@mcp.tool()
def search(query: str, top_k: int = 5) -> str
```

| 引数 | 型 | デフォルト | 説明 |
|------|-----|-----------|------|
| `query` | `str` | — | 検索クエリ |
| `top_k` | `int` | `5` | 返す結果数 |

**戻り値:** 検索結果のテキスト（出典ファイル名・距離スコア付き）

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
    output_lines.append(f"[{i+1}] 出典: {source} (距離: {dist:.2f})")
    output_lines.append(doc)
```

ChromaDB の検索結果は `[0]` で取り出す必要があります（クエリが1つでもリストのリストで返るため）。
距離（distance）の値をそのまま表示します。値が小さいほど類似度が高いことを意味します。

---

### サーバー起動

```python
if __name__ == "__main__":
    mcp.run()
```

`mcp.run()` は stdio 経由の JSON-RPC リスナーを起動します。stdin からリクエストを読み、stdout にレスポンスを書きます。
