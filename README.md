# MCP RAG from scratch

MCP を使った RAG のシンプルな実装です。
コード量が少ないので、MCP や RAG の基本的な流れを追いやすいと思います。

サンプルデータとして架空の野球選手「大堀翔」に関するテキストが入っています。
大堀翔について質問すると LLM が検索ツールを呼び出し、RAG による回答が返ります。
それ以外の質問には LLM が直接回答します。

---

## MCP とは？

**MCP（Model Context Protocol）** は、LLM に「外部ツール」を使わせるための通信規格です。

LLM は単体だとテキスト生成しかできませんが、MCP サーバーが提供するツール（検索、計算、API 呼び出しなど）を使えるようになります。
通信は **JSON-RPC** で行われ、クライアント（LLM 側）とサーバー（ツール側）が役割分担します。

> **JSON-RPC とは？**
> JSON 形式で「メソッド名」と「引数」を送り、「結果」を受け取るだけのシンプルな通信ルールです。
> HTTP の REST API に似ていますが、MCP では標準入出力（stdio）を使って親子プロセス間で直接やりとりします。
> 中身はただの JSON なので、人間が読んでも何をしているか分かりやすいのが特徴です。

```
クライアント                    サーバー
    │  ── initialize ──→          │   接続を確立
    │  ── tools/list ──→          │   使えるツールの一覧を取得
    │  ── tools/call ──→          │   ツールを実行して結果を返す
    │  ←── 検索結果 ────          │
```

このプロジェクトでは、クライアントとサーバーの両方を自作することで、この仕組みを体験できます。

---

## RAG とは？

**RAG（Retrieval-Augmented Generation）** は、LLM に「知らない情報」を答えさせるための手法です。

LLM は学習データにない情報（社内文書、最新ニュースなど）を知りません。
RAG では、質問に関連する文書を**先に検索**して、その内容を LLM に渡してから回答を生成させます。

```
1. ユーザー: 「大堀翔の成績は？」
2. 検索:     ChromaDB から関連テキストを取得  ← ここが RAG のポイント
3. LLM:     検索結果を読んで回答を生成
```

このプロジェクトでは、ChromaDB（ベクトルデータベース）を使って類似度検索を行い、
MCP のツール呼び出しとして RAG を実現しています。

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

<details>
<summary><strong>📖 コラム: Ollama のインストールと qwen3:14b の導入</strong></summary>

このプロジェクトはモック LLM で動作確認できますが、実際の LLM を使うとツール呼び出しの判断や回答生成がよりリアルになります。
ここでは Ollama を使ってローカル LLM を動かす手順を紹介します。

### 1. Ollama のインストール

```bash
# Linux
curl -fsSL https://ollama.com/install.sh | sh

# macOS（Homebrew）
brew install ollama
```

Windows の場合は [ollama.com](https://ollama.com/) からインストーラーをダウンロードしてください。

### 2. Ollama を起動

```bash
ollama serve
```

別ターミナルで実行するか、バックグラウンドで起動します。
macOS / Windows のデスクトップアプリを使っている場合は自動で起動しています。

### 3. qwen3:14b をダウンロード

```bash
ollama pull qwen3:14b
```

約 9GB のダウンロードになります。完了すると `ollama list` に表示されます。

### 4. 動作確認

```bash
ollama run qwen3:14b "こんにちは"
```

応答が返ってくれば準備完了です。このプロジェクトでは `USE_OLLAMA=1` を付けて起動すると Ollama が使われます。

### メモリの目安

| モデル | 必要 VRAM/RAM |
|--------|--------------|
| qwen3:8b | 約 5GB |
| qwen3:14b | 約 9GB |

GPU メモリが足りない場合は CPU でも動きますが、応答が遅くなります。
小さいモデルを使いたい場合は環境変数で変更できます。

```bash
OLLAMA_MODEL=qwen3:8b USE_OLLAMA=1 PYTHONPATH=src uv run python -m client.main
```

</details>

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
