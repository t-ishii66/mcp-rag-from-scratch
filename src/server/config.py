"""
設定ファイル

環境変数があれば使い、なければデフォルト値を使う。
シンプルに辞書で管理。
"""

import os
from pathlib import Path

# プロジェクトのルートディレクトリ
# このファイル(config.py)から2階層上がルート
PROJECT_ROOT = Path(__file__).parent.parent.parent

# 設定値（環境変数 or デフォルト）
CONFIG = {
    # テキストファイルの置き場所
    "documents_path": Path(os.environ.get(
        "RAG_DOCUMENTS_PATH",
        PROJECT_ROOT / "data" / "documents"
    )),

    # ChromaDBの保存先
    "chroma_path": Path(os.environ.get(
        "RAG_CHROMA_PATH",
        PROJECT_ROOT / "chroma_db"
    )),

    # チャンク分割の設定（文脈が切れすぎないよう中程度に設定）
    "chunk_size": int(os.environ.get("RAG_CHUNK_SIZE", "400")),
    "chunk_overlap": int(os.environ.get("RAG_CHUNK_OVERLAP", "80")),

    # 使用するLLMモデル
    "ollama_model": os.environ.get("OLLAMA_MODEL", "qwen3:14b"),

    # 埋め込みモデル（初回起動時に Hugging Face から自動ダウンロードされる、約470MB）
    "embedding_model": "intfloat/multilingual-e5-small",
}
