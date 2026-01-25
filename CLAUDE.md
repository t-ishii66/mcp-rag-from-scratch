# mcp-rag-server

教育目的のMCPプロジェクト。MCPプロトコルの仕組みを学ぶため、クライアントとサーバーの両方を自作する。

## コンセプト

```
┌─────────────────────────────────────────────────────────────┐
│                    MCPクライアント                           │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐ │
│  │ ユーザー入力 │ ──→ │   Ollama    │ ──→ │ ツール判定   │ │
│  └─────────────┘      │  (ローカル   │      └──────┬──────┘ │
│                       │    LLM)     │             │        │
│  ┌─────────────┐      └─────────────┘             │        │
│  │  回答出力   │ ←── 回答生成 ←── 検索結果 ←─────┘        │
│  └─────────────┘                                           │
└─────────────────────────────────────────────────────────────┘
                                │
                          MCPプロトコル
                           (stdio通信)
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                     MCPサーバー                              │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐ │
│  │ ツール定義   │      │  search()   │ ──→ │  ChromaDB   │ │
│  │ (search)    │      │  実行       │ ←── │  クエリ     │ │
│  └─────────────┘      └─────────────┘      └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 学習目標

1. **MCPプロトコル**: クライアント・サーバー間の通信仕様を理解
2. **Ollama tool calling**: LLMがツールを呼び出す仕組みを理解
3. **RAGの基本**: ベクトル検索による関連文書取得を理解
4. **全体フロー**: 質問→ツール判定→検索→回答生成の流れを体験

## 技術スタック

- **言語**: Python 3.11+
- **LLM**: Ollama (ローカル実行)
- **MCP SDK**: mcp (公式Python SDK)
- **ベクトルDB**: ChromaDB (永続化モード)
- **埋め込み**: ChromaDB標準 (all-MiniLM-L6-v2)
- **パッケージ管理**: uv

## ディレクトリ構造

```
mcp-rag-server/
├── CLAUDE.md
├── pyproject.toml
├── src/
│   ├── client/
│   │   ├── __init__.py
│   │   └── main.py           # MCPクライアント + Ollama連携
│   └── server/
│       ├── __init__.py
│       ├── main.py           # MCPサーバー本体
│       ├── indexer.py        # テキストファイルのインデックス処理
│       └── config.py         # 設定管理
├── data/
│   └── documents/            # インデックス対象の.txtファイル配置場所
└── chroma_db/                # ChromaDB永続化ディレクトリ
```

## コンポーネント詳細

### 1. MCPサーバー (`src/server/`)

テキスト検索ツールを提供する。

#### ツール定義

```python
@server.tool()
async def search(query: str, top_k: int = 5) -> list[dict]:
    """
    ChromaDBから関連テキストを検索する。

    Args:
        query: 検索クエリ
        top_k: 返す結果数

    Returns:
        関連テキストのリスト（出典ファイル名付き）
    """
```

#### 初期化処理

1. `data/documents/` 内の `.txt` ファイルを走査
2. テキストをチャンクに分割（500文字、100文字オーバーラップ）
3. ChromaDBにベクトル化して保存

### 2. MCPクライアント (`src/client/`)

Ollamaと連携し、ユーザーとの対話を管理する。

#### 処理フロー

```python
# 1. ユーザーからの質問を受け取る
user_input = input("質問: ")

# 2. Ollamaに送信（ツール定義付き）
response = ollama.chat(
    model="qwen2.5:latest",
    messages=[{"role": "user", "content": user_input}],
    tools=[search_tool_definition]
)

# 3. ツール呼び出しが必要か判定
if response.tool_calls:
    # 4. MCPサーバーにツール実行を依頼
    result = await mcp_client.call_tool("search", args)

    # 5. 結果をOllamaに戻して回答生成
    final_response = ollama.chat(
        messages=[...previous, {"role": "tool", "content": result}]
    )
```

## 設定

| 設定項目 | 環境変数 | デフォルト値 |
|---------|---------|-------------|
| ドキュメントフォルダ | `RAG_DOCUMENTS_PATH` | `./data/documents` |
| ChromaDB保存先 | `RAG_CHROMA_PATH` | `./chroma_db` |
| チャンクサイズ | `RAG_CHUNK_SIZE` | `500` |
| オーバーラップ | `RAG_CHUNK_OVERLAP` | `100` |
| Ollamaモデル | `OLLAMA_MODEL` | `qwen2.5:latest` |

## 開発コマンド

```bash
# 依存関係インストール
uv sync

# Ollamaが起動していることを確認
ollama list

# ドキュメントのインデックス作成
uv run python -m server.indexer

# MCPサーバー単体起動（デバッグ用）
uv run python -m server.main

# クライアント起動（通常利用）
uv run python -m client.main
```

## デバッグ方法

### MCP Inspector での動作確認

MCPサーバー単体の動作を確認する場合:

```bash
npx @modelcontextprotocol/inspector uv run python -m server.main
```

### ログ出力

通信内容を確認するため、詳細ログを有効化:

```bash
RAG_LOG_LEVEL=DEBUG uv run python -m client.main
```

## 依存パッケージ

```toml
[project]
dependencies = [
    "mcp>=1.0.0",
    "chromadb>=0.4.0",
    "ollama>=0.1.0",
]
```

## 前提条件

1. **Ollama**: インストール済みで、モデルがダウンロード済み
   ```bash
   ollama pull qwen2.5:latest
   ```

2. **Python 3.11+**: uv でインストール管理

## コーディング規約

- 型ヒントを必須とする
- docstringはGoogle形式
- エラーは適切な例外クラスで処理
- ログは`logging`モジュールを使用

## 教育目的の設計方針

このプロジェクトは**初心者がコードを読んで動作を理解する**ことが最優先目標。

### 基本原則: 最小限のシンプルさ

- **これ以上削ったら意味がなくなる**というレベルまでシンプルに
- 本格的な実装より「動きが見える」ことを重視
- 1ファイルで完結できるなら1ファイルに
- クラスより関数、関数よりベタ書きを優先
- 抽象化・再利用性・拡張性は考えない

### コードの書き方

- 各処理が何をしているか、日本語コメントで説明
- 変数名は日本語でも良い（理解しやすさ優先）
- エラー処理は最小限（ハッピーパスのみ）
- 設定は直書き or 最小限の変数で
- pytestのフィクスチャ等の高度な機能は避ける

### ファイル構成

```
良い例: 50行で動作が一目瞭然
悪い例: 200行で本格的だが読むのに時間がかかる
```

### テストの書き方

```python
# 良い例: 何をしているか一目でわかる
def test_chromadb_search():
    # 1. DBを作る
    client = chromadb.Client()
    collection = client.create_collection("test")

    # 2. データを入れる
    collection.add(ids=["1"], documents=["大谷翔平は野球選手"])

    # 3. 検索する
    results = collection.query(query_texts=["野球"], n_results=1)

    # 4. 結果を確認
    assert "大谷" in results["documents"][0][0]
```
