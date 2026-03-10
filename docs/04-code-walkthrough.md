# コード解説

このプロジェクトの全ソースコードの概要です。
各ファイルの詳細なリファレンスはリンク先を参照してください。

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

## 各ファイルの概要

### 1. `src/server/config.py` — 設定管理（38行）

環境変数からの設定読み込みを辞書1つで管理します。
`PROJECT_ROOT` をファイルパスから算出し、`CONFIG` 辞書でドキュメントフォルダ・ChromaDB 保存先・チャンクサイズなどを一元管理します。

→ [詳細リファレンス](refs/config.md)

### 2. `src/server/indexer.py` — インデックス作成（158行）

テキストファイルを読み込み、チャンクに分割して ChromaDB に保存します。
`load_text_files()` でファイル読み込み → `split_into_chunks()` でチャンク分割 → `index_documents()` で ChromaDB に保存、という3ステップの処理です。

→ [詳細リファレンス](refs/indexer.md)

### 3. `src/server/main.py` — MCP サーバー（122行）

ChromaDB の検索ツールを MCP プロトコルで提供するサーバーです。
`@mcp.tool()` で登録された `search()` 関数がベクトル検索を実行し、出典ファイル名・距離スコア付きの結果を返します。ChromaDB への接続は初回呼び出しまで遅延されます。

→ [詳細リファレンス](refs/server.md)

### 4. `src/client/main.py` — MCP クライアント（281行）

MCP サーバーに接続し、LLM（Ollama or モック）と連携してユーザーと対話するクライアントです。
サーバーを子プロセスとして起動 → ツール一覧を取得 → ユーザーの質問を LLM に送信 → 必要に応じてツール実行 → 回答生成、という流れで動作します。

→ [詳細リファレンス](refs/client.md)

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
