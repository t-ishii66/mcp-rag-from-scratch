# TODO.md - 実装計画

各ステップで実装とテストを行い、動作を確認しながら進める。

## Step 1: プロジェクト初期セットアップ ✅

- [x] `pyproject.toml` 作成
- [x] ディレクトリ構造作成
- [x] `uv sync` で依存関係インストール
- [x] **テスト**: `uv run python -c "import mcp; import chromadb; import ollama; print('OK')"` で依存確認

## Step 2: ChromaDBの基本動作確認 ✅

- [x] `src/server/config.py` 作成（設定管理）
- [x] `tests/test_chromadb.py` 作成
- [x] **テスト**: ChromaDBへのドキュメント追加・検索が動作することを確認
  - ベクトル化
  - 類似検索
  - メタデータ（ファイル名）の保存
- [x] 野球に関するテキストファイル6件を `data/documents/` に配置

## Step 3: インデクサーの実装 ✅

- [x] `src/server/indexer.py` 作成
  - テキストファイル読み込み
  - チャンク分割
  - ChromaDBへの保存
- [x] `data/documents/` にサンプル `.txt` ファイルを配置
- [x] **テスト**: `tests/test_indexer.py` でインデックス作成を確認

## Step 4: MCPサーバーの実装 ✅

- [x] `src/server/__init__.py` 作成
- [x] `src/server/main.py` 作成
  - MCPサーバー初期化（FastMCP使用）
  - `search` ツール定義
  - デバッグログ機能（`RAG_DEBUG=1`でJSON-RPC通信確認可能）
- [x] **テスト**: MCP Inspector で動作確認
  ```bash
  npx @modelcontextprotocol/inspector env PYTHONPATH=src RAG_DEBUG=1 uv run python -m server.main
  ```

## Step 5: Ollama tool calling の動作確認

- [ ] `tests/test_ollama_tools.py` 作成
- [ ] **テスト**: Ollamaがツール定義を受け取り、ツール呼び出しを返すことを確認
  - ツール定義のJSON形式
  - tool_calls の解析方法

## Step 6: MCPクライアントの実装

- [ ] `src/client/__init__.py` 作成
- [ ] `src/client/main.py` 作成
  - MCPサーバーへの接続
  - Ollamaとの連携
  - 対話ループ
- [ ] **テスト**: `tests/test_client.py` でMCP通信を確認

## Step 7: 統合テスト

- [ ] 全体フローのテスト
  - ユーザー質問 → Ollama → ツール判定 → MCP検索 → 回答生成
- [ ] エラーハンドリングの確認
- [ ] ログ出力の確認

---

## 進捗管理

| Step | 状態 | 備考 |
|------|------|------|
| 1 | 完了 | pyenv 3.11.14 + uv |
| 2 | 完了 | 野球テキスト6件 + ChromaDBテスト15件 |
| 3 | 完了 | indexer.py + テスト4件 |
| 4 | 完了 | FastMCP + デバッグログ |
| 5 | 未着手 | |
| 6 | 未着手 | |
| 7 | 未着手 | |
