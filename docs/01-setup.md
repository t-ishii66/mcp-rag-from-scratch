# 環境構築ガイド

このプロジェクトを動かすために必要なツールのインストール手順です。
本ガイドおよびプロジェクト内の全コマンドは **uv** を前提にしています。uv は Python 本体のダウンロードも自動で行うため、手順がもっともシンプルです。

## 必要なもの

| ツール | 必須？ | 用途 |
|--------|--------|------|
| uv | 必須 | Python 本体とパッケージの管理 |
| Ollama | 任意 | ローカル LLM（モック LLM でも動作確認可能） |

## 1. uv のインストール

[uv](https://docs.astral.sh/uv/) は Python 本体のインストールからパッケージ管理まで一括で行えるツールです。
**Python を別途インストールする必要はありません**——`uv sync` が `pyproject.toml` の設定に基づいて適切なバージョンの Python を自動でダウンロードしてくれます。

```bash
# Linux / macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# または Homebrew
brew install uv
```

インストール確認:

```bash
uv --version
```

## 2. プロジェクトのセットアップ

```bash
# リポジトリをクローン
git clone https://github.com/t-ishii66/mcp-rag-from-scratch.git
cd mcp-rag-from-scratch

# 依存関係をインストール
uv sync
```

`uv sync` を実行すると以下のパッケージがインストールされます:

| パッケージ | バージョン | 役割 |
|-----------|-----------|------|
| `mcp` | >= 1.0.0 | MCP プロトコルの公式 Python SDK |
| `chromadb` | >= 0.4.0 | ベクトルデータベース |
| `ollama` | >= 0.4.0 | Ollama Python クライアント |
| `sentence-transformers` | >= 2.2.0 | テキスト埋め込みモデル |

## 3. ドキュメントのインデックス作成

`data/documents/` にあるサンプルのテキストファイルを ChromaDB に登録します。初回のみ必要です。

```bash
PYTHONPATH=src uv run python -m server.indexer
```

動作を理解したあとは、`data/documents/` のファイルを自分のテキストデータに差し替えてインデックスを再作成すれば、オリジナルの RAG を試せます。

出力例:

```
=== インデックス作成開始 ===
ドキュメントフォルダ: /path/to/data/documents
ChromaDB保存先: /path/to/chroma_db

[1] テキストファイル読み込み
  読み込み: profile.txt (1234文字)
  読み込み: stats.txt (2345文字)
  ...
  → 7ファイル読み込み完了

[2] ChromaDB初期化
  コレクション 'documents' を作成
  埋め込みモデル: intfloat/multilingual-e5-small

[3] チャンク分割とインデックス作成
  profile.txt: 4チャンク
  stats.txt: 8チャンク
  ...

=== 完了: 42チャンクをインデックス ===
```

初回実行時には埋め込みモデル（約 470MB）が Hugging Face から自動ダウンロードされます。
2回目以降はキャッシュが使われるため高速です。

## 4. 動作確認

### モック LLM で確認（Ollama 不要）

```bash
PYTHONPATH=src uv run python -m client.main
```

「大堀翔の成績は？」と入力して回答が返れば成功です。

### Ollama を使う場合（任意）

モック LLM でも動作しますが、Ollama を使うとより自然な回答が得られます。

#### Ollama のインストール

```bash
# Linux
curl -fsSL https://ollama.com/install.sh | sh

# macOS（Homebrew）
brew install ollama
```

Windows の場合は [ollama.com](https://ollama.com/) からインストーラーをダウンロードしてください。

#### Ollama の起動とモデルのダウンロード

```bash
# Ollama を起動（別ターミナルで実行）
ollama serve

# モデルをダウンロード（約 9GB）
ollama pull qwen3:14b
```

#### Ollama モードで起動

```bash
USE_OLLAMA=1 PYTHONPATH=src uv run python -m client.main
```

#### メモリの目安

| モデル | 必要 VRAM / RAM |
|--------|----------------|
| qwen3:8b | 約 5GB |
| qwen3:14b | 約 9GB |

GPU メモリが足りない場合は CPU でも動きますが応答が遅くなります。
小さいモデルを使う場合は環境変数で変更できます:

```bash
OLLAMA_MODEL=qwen3:8b USE_OLLAMA=1 PYTHONPATH=src uv run python -m client.main
```

## テストの実行

```bash
uv run pytest
```

全テストが通れば環境構築は完了です。

## 環境変数の一覧

| 環境変数 | デフォルト値 | 説明 |
|---------|-------------|------|
| `RAG_DOCUMENTS_PATH` | `./data/documents` | テキストファイルの置き場所 |
| `RAG_CHROMA_PATH` | `./chroma_db` | ChromaDB の保存先 |
| `RAG_CHUNK_SIZE` | `400` | チャンク分割の文字数 |
| `RAG_CHUNK_OVERLAP` | `80` | チャンク間の重複文字数 |
| `OLLAMA_MODEL` | `qwen3:14b` | 使用する LLM モデル |
| `USE_OLLAMA` | (未設定) | `1` にすると Ollama を使用 |
| `RAG_DEBUG` | (未設定) | `1` にするとデバッグログを表示 |

## よくあるトラブル

### `ModuleNotFoundError: No module named 'server'`

`PYTHONPATH=src` を付けていない可能性があります。

```bash
# NG
uv run python -m client.main

# OK
PYTHONPATH=src uv run python -m client.main
```

### 検索結果が出ない

`data/documents/` にテキストファイルがあるか確認し、インデックスを再作成してください。

```bash
PYTHONPATH=src uv run python -m server.indexer
```

### 初回起動が遅い

埋め込みモデル（約 470MB）のダウンロードが走っています。
2回目以降はキャッシュされるため高速です。
