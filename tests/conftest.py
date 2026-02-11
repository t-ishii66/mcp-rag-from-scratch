"""
テスト用の共通フィクスチャとセットアップ

すべてのテスト実行前に、ChromaDBのインデックスを初期化する。
"""

import pytest
import shutil
import sys
from pathlib import Path

# srcをPythonパスに追加（テスト実行時のインポート問題を解決）
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from server.indexer import index_documents
from server.config import CONFIG


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """テスト用のChromaDBを初期化する"""
    chroma_path = Path(CONFIG["chroma_path"])
    documents_path = Path(CONFIG["documents_path"])
    
    # テスト用ChromaDB（テスト実行時に毎回作成）
    # 既存のデータベースをリセット
    if chroma_path.exists():
        shutil.rmtree(chroma_path)
    
    chroma_path.mkdir(parents=True, exist_ok=True)
    
    # インデックスを作成
    if documents_path.exists():
        print(f"\nテストDB初期化: {documents_path} からインデックスを作成")
        index_documents(
            documents_path=documents_path,
            chroma_path=chroma_path,
            chunk_size=CONFIG["chunk_size"],
            chunk_overlap=CONFIG["chunk_overlap"],
        )
    
    yield
    
    # テスト完了後のクリーンアップは不要（次回実行時にリセット）
