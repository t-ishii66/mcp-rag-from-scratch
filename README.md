# MCP RAG from scratch

MCP を使った RAG のシンプルな実装です。
コード量が少ないので、MCP や RAG の基本的な流れを追いやすいと思います。

サンプルデータとして架空の野球選手「大堀翔」に関するテキストが入っています。
大堀翔について質問すると LLM が検索ツールを呼び出し、RAG による回答が返ります。
それ以外の質問には LLM が直接回答します。

---

## プロジェクト構成

- `src/server/main.py` — MCP サーバー。`search` ツールを定義し ChromaDB を検索します。
- `src/server/indexer.py` — `data/documents` を読み込み、チャンク化して ChromaDB へ保存します。
- `src/server/config.py` — モデル名やチャンクサイズ等の設定。
- `src/client/main.py` — MCP に接続し、LLM がツールを呼ぶか判断→検索→回答生成まで行います。

---

## 前提条件

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- Ollama は任意（モック LLM でも動作確認できます）

---

## 動かし方

1. 依存関係をインストール
   ```bash
   uv sync
   ```

2. ドキュメントをインデックス
   ```bash
   PYTHONPATH=src uv run python -m server.indexer
   ```

3. クライアントを起動（モック LLM）
   ```bash
   PYTHONPATH=src uv run python -m client.main
   ```

4. Ollama を使う場合
   ```bash
   USE_OLLAMA=1 PYTHONPATH=src uv run python -m client.main
   ```

---

## Ollama のモデル設定

`qwen3:14b` で動作確認しています。
他のモデルを使う場合は `src/server/config.py` の `OLLAMA_MODEL` を変更するか、環境変数で指定してください。

```bash
# 環境変数で変更する場合
OLLAMA_MODEL=gemma3:12b USE_OLLAMA=1 PYTHONPATH=src uv run python -m client.main
```

---

## テスト

```bash
uv run pytest
```

---

## ChromaDB だけを試す

MCP や LLM を介さず、ChromaDB の検索結果だけを確認できるスクリプトがあります。

```bash
uv run python tools/query_chromadb.py
```

`クエリ>` に検索語を入力します。上位件数は `クエリ /3` の形式で指定できます。

---

## デバッグ: JSON-RPC 通信の可視化

`RAG_DEBUG=1` を付けると、MCP クライアント・サーバー間の JSON-RPC メッセージが表示されます。
`initialize` → `tools/list` → `tools/call` の流れが見えるので、MCP プロトコルの理解に役立ちます。

```bash
RAG_DEBUG=1 PYTHONPATH=src uv run python -m client.main
```

出力例:

```
[JSON-RPC] → 送信: tools/call
{
  "method": "tools/call",
  "params": {
    "name": "search",
    "arguments": {"query": "大堀翔の成績"}
  }
}

[JSON-RPC] ← 受信: tools/call
{
  "content": [
    {
      "type": "text",
      "text": "[1] 出典: stats.txt (類似度: 0.91)\npassage: 大堀翔の詳細成績データ..."
    }
  ]
}
```

---

## データの差し替え

`data/documents` の `.txt` ファイルを差し替えれば、別の用途の検索ツールになります。

1. `data/documents` のテキストを編集
2. インデックスを再作成
   ```bash
   PYTHONPATH=src uv run python -m server.indexer
   ```
3. クライアントを起動して動作確認

---

## よくあるつまずき

- `PYTHONPATH=src` を付けないとモジュールが見つからない
- `data/documents` が空だと検索結果が出ない
- Ollama を使う場合は `USE_OLLAMA=1` が必要
- 初回起動時に埋め込みモデル（約 470MB）の自動ダウンロードが走ります。2回目以降はキャッシュが使われます
