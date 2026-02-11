"""
インデクサーのテスト

テスト用の一時ファイルを使い、実際のdata/documentsには依存しない。
"""

import tempfile
from pathlib import Path
import sys

# src/serverをインポートパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "server"))

from indexer import load_text_files, split_into_chunks, index_documents
import chromadb


def test_split_into_chunks_short_text():
    """短いテキストはそのまま1チャンクになる"""
    text = "これは短いテキストです。"
    chunks = split_into_chunks(text, chunk_size=500, overlap=100)

    assert len(chunks) == 1
    assert chunks[0] == text


def test_split_into_chunks_long_text():
    """長いテキストは複数チャンクに分割される"""
    # 100文字のテキストを作成
    text = "あ" * 100

    # 30文字ごとに分割、10文字オーバーラップ
    chunks = split_into_chunks(text, chunk_size=30, overlap=10)

    # 期待: 30文字、次は20文字進んで30文字、...
    # 0-30, 20-50, 40-70, 60-90, 80-100
    assert len(chunks) == 5
    assert len(chunks[0]) == 30
    assert len(chunks[-1]) == 20  # 最後は残り


def test_load_text_files():
    """テキストファイルの読み込みをテスト"""
    # 一時ディレクトリにテストファイルを作成
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # テスト用ファイルを作成
        (tmppath / "test1.txt").write_text("テスト内容1", encoding="utf-8")
        (tmppath / "test2.txt").write_text("テスト内容2", encoding="utf-8")
        (tmppath / "other.md").write_text("これは無視される", encoding="utf-8")

        # 読み込み実行
        documents = load_text_files(tmppath)

        # .txtファイルのみ2件読み込まれる
        assert len(documents) == 2

        # ファイル名と内容が正しく取得できている
        filenames = [d["filename"] for d in documents]
        assert "test1.txt" in filenames
        assert "test2.txt" in filenames


def test_index_documents():
    """インデックス作成の全体フローをテスト"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        docs_path = tmppath / "documents"
        chroma_path = tmppath / "chroma_db"
        docs_path.mkdir()

        # テスト用ドキュメントを作成（短いので1チャンクずつ）
        (docs_path / "野球.txt").write_text(
            "野球は9人対9人で行うスポーツです。",
            encoding="utf-8"
        )
        (docs_path / "サッカー.txt").write_text(
            "サッカーは11人対11人で行うスポーツです。",
            encoding="utf-8"
        )

        # インデックス作成
        total = index_documents(
            documents_path=docs_path,
            chroma_path=chroma_path,
            chunk_size=500,
            chunk_overlap=100,
            collection_name="test_collection",
        )

        # 2ファイル×1チャンク = 2チャンク
        assert total == 2

        # ChromaDBに保存されたことを確認
        client = chromadb.PersistentClient(path=str(chroma_path))
        collection = client.get_collection("test_collection")

        # 「野球」で検索すると野球のドキュメントがヒット
        results = collection.query(query_texts=["野球"], n_results=1)
        assert "野球" in results["documents"][0][0]
        assert results["metadatas"][0][0]["source"] == "野球.txt"
