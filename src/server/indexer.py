"""
インデクサー

テキストファイルを読み込み、チャンクに分割してChromaDBに保存する。
"""

import chromadb
from pathlib import Path
from server.config import CONFIG


def load_text_files(documents_path: Path) -> list[dict]:
    """
    指定フォルダ内の.txtファイルを読み込む。

    Returns:
        [{"filename": "xxx.txt", "content": "..."}, ...]
    """
    documents = []

    for txt_file in documents_path.glob("*.txt"):
        content = txt_file.read_text(encoding="utf-8")
        documents.append({
            "filename": txt_file.name,
            "content": content,
        })
        print(f"  読み込み: {txt_file.name} ({len(content)}文字)")

    return documents


def split_into_chunks(text: str, chunk_size: int, overlap: int) -> list[str]:
    """
    テキストを指定サイズのチャンクに分割する。

    Args:
        text: 分割対象のテキスト
        chunk_size: 1チャンクの文字数
        overlap: チャンク間の重複文字数

    Returns:
        チャンクのリスト
    """
    # テキストが短ければそのまま返す
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)

        # 次の開始位置（overlapぶん戻る）
        start = end - overlap

    return chunks


def index_documents(
    documents_path: Path,
    chroma_path: Path,
    chunk_size: int,
    chunk_overlap: int,
    collection_name: str = "documents",
) -> int:
    """
    テキストファイルをChromaDBにインデックスする。

    Args:
        documents_path: テキストファイルのフォルダ
        chroma_path: ChromaDB保存先
        chunk_size: チャンクサイズ
        chunk_overlap: オーバーラップ
        collection_name: コレクション名

    Returns:
        インデックスしたチャンク数
    """
    print(f"=== インデックス作成開始 ===")
    print(f"ドキュメントフォルダ: {documents_path}")
    print(f"ChromaDB保存先: {chroma_path}")

    # 1. テキストファイルを読み込む
    print("\n[1] テキストファイル読み込み")
    documents = load_text_files(documents_path)
    print(f"  → {len(documents)}ファイル読み込み完了")

    if not documents:
        print("警告: テキストファイルが見つかりません")
        return 0

    # 2. ChromaDBクライアントを作成（永続化モード）
    print("\n[2] ChromaDB初期化")
    client = chromadb.PersistentClient(path=str(chroma_path))

    # 既存のコレクションがあれば削除して新規作成
    existing = [c.name for c in client.list_collections()]
    if collection_name in existing:
        client.delete_collection(collection_name)
        print(f"  既存のコレクション '{collection_name}' を削除")

    collection = client.create_collection(name=collection_name)
    print(f"  コレクション '{collection_name}' を作成")

    # 3. 各ドキュメントをチャンクに分割してDBに追加
    print("\n[3] チャンク分割とインデックス作成")
    total_chunks = 0

    for doc in documents:
        chunks = split_into_chunks(doc["content"], chunk_size, chunk_overlap)
        print(f"  {doc['filename']}: {len(chunks)}チャンク")

        for i, chunk in enumerate(chunks):
            # 一意のIDを生成（ファイル名_チャンク番号）
            chunk_id = f"{doc['filename']}_{i}"

            collection.add(
                ids=[chunk_id],
                documents=[chunk],
                metadatas=[{
                    "source": doc["filename"],
                    "chunk_index": i,
                }],
            )
            total_chunks += 1

    print(f"\n=== 完了: {total_chunks}チャンクをインデックス ===")
    return total_chunks


# 直接実行された場合
if __name__ == "__main__":
    index_documents(
        documents_path=CONFIG["documents_path"],
        chroma_path=CONFIG["chroma_path"],
        chunk_size=CONFIG["chunk_size"],
        chunk_overlap=CONFIG["chunk_overlap"],
    )
