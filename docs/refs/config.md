# config.py — 設定管理

対応ソース: `src/server/config.py`（38行）

## 概要

環境変数からの設定読み込みを辞書1つで管理する、最もシンプルなファイルです。

## アルゴリズム

1. `Path(__file__)` からプロジェクトルートを算出
2. 各設定値について「環境変数があればそれを使い、なければデフォルト値」のパターンで辞書に格納

## 定数リファレンス

### `PROJECT_ROOT`

```python
PROJECT_ROOT = Path(__file__).parent.parent.parent
```

`config.py` は `src/server/config.py` にあるので、`.parent` を3回呼ぶとプロジェクトルートに到達します:

```
config.py → server/ → src/ → プロジェクトルート
  .parent    .parent   .parent
```

### `CONFIG` 辞書

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

| キー | 環境変数 | デフォルト値 | 説明 |
|------|---------|-------------|------|
| `documents_path` | `RAG_DOCUMENTS_PATH` | `<root>/data/documents` | テキストファイルの置き場所 |
| `chroma_path` | `RAG_CHROMA_PATH` | `<root>/chroma_db` | ChromaDB の保存先 |
| `chunk_size` | `RAG_CHUNK_SIZE` | `400` | 1チャンクの文字数 |
| `chunk_overlap` | `RAG_CHUNK_OVERLAP` | `80` | チャンク間の重複文字数 |
| `ollama_model` | `OLLAMA_MODEL` | `qwen3:1.7b` | 使用する LLM モデル |
| `embedding_model` | —（固定値） | `intfloat/multilingual-e5-small` | 埋め込みモデル |

`embedding_model` だけは環境変数なしの固定値です。E5 モデルは埋め込み時のプレフィックス規約があるため、気軽に変更できません。
