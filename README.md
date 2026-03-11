![](top.png)

# MCP RAG from scratch

**MCP と RAG を「完全自作」して仕組みを理解する**、ハンズオン型の学習プロジェクトです。

サンプルデータとして架空の野球選手「大堀翔」に関するテキストが入っています。
大堀翔について質問すると LLM が検索ツールを呼び出し、RAG による回答が返ります。
それ以外の質問には LLM が直接回答します。

---

## このプロジェクトで学べること

「MCP 対応のアプリを使ったことはあるけど、中で何が起きているか分からない」——そんな疑問を解消するために、クライアントとサーバーの両方をゼロから書きます。

- **MCP プロトコル** — LLM がツールを呼び出す仕組み（JSON-RPC over stdio）
- **RAG（検索拡張生成）** — ベクトル検索で関連ドキュメントを取得し、回答に活用する流れ
- **Ollama tool calling** — ローカル LLM にツールを使わせる方法

すべてローカルで完結し、API キーは不要です。

## アーキテクチャ

```
質問: 「大堀翔の年俸は？」
         │
         ▼
┌─────────────────────────────┐
│      MCP クライアント        │
│                             │
│  Ollama (ローカル LLM)      │
│    → 「検索が必要だ」と判断  │
│    → search ツールを呼び出し │
└──────────┬──────────────────┘
           │ MCP プロトコル (stdio)
           ▼
┌─────────────────────────────┐
│       MCP サーバー           │
│                             │
│  ChromaDB でベクトル検索     │
│    → 関連チャンクを返却      │
└──────────┬──────────────────┘
           │
           ▼
  回答: 「大堀翔の年俸は○○万円です」
```

## 特徴

- **コード量が少ない** — クライアントとサーバー合わせて約 400 行。全部読めます
- **外部 API 不要** — Ollama でローカル LLM を使うので、インターネット接続がなくても動作
- **日本語コメント付き** — 各処理が何をしているか、コード内のコメントで説明

---

## ドキュメント

| # | ドキュメント | 内容 |
|---|-------------|------|
| 1 | [環境構築ガイド](docs/01-setup.md) | uv・Ollama のインストールからプロジェクトの起動まで |
| 2 | [MCP プロトコル解説](docs/02-mcp-explained.md) | MCP とは何か、JSON-RPC 通信の仕組み、ツール呼び出しの流れ |
| 3 | [RAG 解説](docs/03-rag-explained.md) | RAG の概念、ベクトル検索、チャンク分割、埋め込みモデル |
| 4 | [コード解説](docs/04-code-walkthrough.md) | ソースファイルの概要と、各ファイルの[詳細リファレンス](docs/refs/config.md) |
| 5 | [チュートリアル](docs/05-tutorial.md) | 実際に手を動かして動作確認する手順書 |

## おすすめの読み方

初めての方は以下の順番がおすすめです。

1. **[環境構築ガイド](docs/01-setup.md)** で動かせる状態にする
2. **[チュートリアル](docs/05-tutorial.md)** で実際に動かして全体の流れを体験する
3. **[MCP プロトコル解説](docs/02-mcp-explained.md)** と **[RAG 解説](docs/03-rag-explained.md)** で背景知識を固める
4. **[コード解説](docs/04-code-walkthrough.md)** でソースコードを深く理解する

すでに MCP や RAG を知っている方は、[コード解説](docs/04-code-walkthrough.md) から読み始めても構いません。

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

## 技術スタック

| カテゴリ | 技術 |
|---------|------|
| 言語 | Python 3.11+ |
| LLM | Ollama（ローカル実行） |
| MCP | mcp（公式 Python SDK） |
| ベクトル DB | ChromaDB |
| 埋め込みモデル | intfloat/multilingual-e5-small |
| パッケージ管理 | uv |

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
<summary><strong>📖 コラム: Ollama のインストールと qwen3:1.7b の導入</strong></summary>

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

### 3. qwen3:1.7b をダウンロード

```bash
ollama pull qwen3:1.7b
```

約 1.5GB のダウンロードになります。完了すると `ollama list` に表示されます。

### 4. 動作確認

```bash
ollama run qwen3:1.7b "こんにちは"
```

応答が返ってくれば準備完了です。このプロジェクトでは `USE_OLLAMA=1` を付けて起動すると Ollama が使われます。

### メモリの目安

| モデル | 必要 VRAM/RAM |
|--------|--------------|
| qwen3:1.7b | 約 2GB |
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

`qwen3:1.7b` をデフォルトで使用しています。
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
