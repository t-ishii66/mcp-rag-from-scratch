"""
ChromaDB 対話式クエリツール

data/documents を再読み込みしてChromaDBを初期化し、自由に問い合わせて結果を確認できる。
日本語対応埋め込みモデル (intfloat/multilingual-e5-small) を使用。
終了するには「quit」または Ctrl+C。

使い方:
    uv run python tools/query_chromadb.py
"""

import sys
import os

# sentence-transformersのtqdmプログレスバーを抑制
os.environ["TQDM_DISABLE"] = "1"

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from pathlib import Path

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from server.indexer import index_documents
from server.config import CONFIG

# 日本語対応埋め込みモデル（E5系は prefix 付きが推奨）
EMBEDDING_FUNCTION = SentenceTransformerEmbeddingFunction(
    model_name=CONFIG["embedding_model"]
)
E5_QUERY_PREFIX = "query: "

# ChromaDBの保存先（CONFIG から取得。環境変数 RAG_CHROMA_PATH で変更可能）
CHROMA_PATH = Path(CONFIG["chroma_path"])


def main():
    # === インデックスがなければ作成 ===
    if not CHROMA_PATH.exists():
        print(f"ChromaDB が見つかりません。インデックスを作成します: {CHROMA_PATH}")
        print(f"ドキュメント ({CONFIG['documents_path']}) をインデックス中...")
        index_documents(
            documents_path=Path(CONFIG["documents_path"]),
            chroma_path=CHROMA_PATH,
            chunk_size=CONFIG["chunk_size"],
            chunk_overlap=CONFIG["chunk_overlap"],
        )
    else:
        print(f"既存の ChromaDB を使用: {CHROMA_PATH}")
    print("-" * 50)
    
    # === 初期化後、クエリ対話開始 ===
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))

    # コレクション一覧を表示
    collections = client.list_collections()
    print(f"コレクション一覧: {[c.name for c in collections]}")

    if not collections:
        print("エラー：コレクションがありません。")
        return

    # 最初のコレクションを使う（通常は1つだけ）
    # embedding_function を明示的に指定して、保存時と同じモデルで埋め込みを生成
    collection_name = collections[0].name
    collection = client.get_collection(
        name=collection_name,
        embedding_function=EMBEDDING_FUNCTION
    )
    print(f"使用コレクション: {collection.name} ({collection.count()}件)")
    print("-" * 50)
    print("検索クエリを入力してください（quit で終了）")
    print()

    while True:
        try:
            query = input("クエリ> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n終了")
            break

        if not query or query == "quit":
            print("終了")
            break

        # 簡易クエリ補正: 年度だけ聞かれる場合は「年俸」を補う
        if ("年俸" not in query) and (any(ch.isdigit() for ch in query) or "年" in query):
            query = f"年俸 {query}"

        # n_results を指定できる（例: "大堀翔 /3" で上位3件）
        n_results = 5
        if " /" in query:
            parts = query.rsplit(" /", 1)
            query = parts[0]
            try:
                n_results = int(parts[1])
            except ValueError:
                pass

        # 検索実行
        results = collection.query(
            query_texts=[f"{E5_QUERY_PREFIX}{query}"],
            n_results=n_results,
        )

        # 結果表示
        docs = results["documents"][0]
        distances = results["distances"][0]
        metadatas = results["metadatas"][0]

        print(f"\n--- 検索結果 ({len(docs)}件) ---")
        for i, (doc, dist, meta) in enumerate(zip(docs, distances, metadatas)):
            source = meta.get("source", "不明")
            # E5のprefixを表示用に除去
            display_doc = doc.replace("passage: ", "", 1)
            # 見出し（■）があれば先に表示
            heading = ""
            for line in display_doc.splitlines():
                if line.strip().startswith("■"):
                    heading = line.strip()
                    break
            # テキストが長い場合は300文字で切る
            preview = display_doc[:300] + "..." if len(display_doc) > 300 else display_doc
            print(f"  [{i+1}] 距離={dist:.4f}  出典={source}")
            if heading:
                print(f"      {heading}")
            print(f"      {preview}")
        print()


if __name__ == "__main__":
    main()
