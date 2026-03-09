"""
MCPサーバー

ChromaDBを使った検索ツールを提供する。
JSON-RPC 2.0プロトコルでstdio通信を行う。

デバッグモード:
  RAG_DEBUG=1 で起動すると、JSON-RPC通信の内容をstderrに出力する。
"""

import sys
import os

# sentence-transformersのtqdmプログレスバーを抑制
os.environ["TQDM_DISABLE"] = "1"

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from mcp.server.fastmcp import FastMCP

from server.config import CONFIG

# デバッグモードの判定
DEBUG = os.environ.get("RAG_DEBUG", "").lower() in ("1", "true", "yes")


def debug_log(message: str) -> None:
    """デバッグログをstderrに出力（stdoutはJSON-RPC通信で使用）"""
    if DEBUG:
        print(f"[DEBUG] {message}", file=sys.stderr)


# MCPサーバーを作成
mcp = FastMCP("rag-search-server")

# 日本語対応埋め込みモデル（E5系は prefix 付きが推奨）
EMBEDDING_FUNCTION = SentenceTransformerEmbeddingFunction(
    model_name=CONFIG["embedding_model"]
)
E5_QUERY_PREFIX = "query: "

# ChromaDBコレクション（初回アクセス時に接続する）
_collection = None


def get_collection():
    """ChromaDBコレクションを取得する（初回のみ接続）"""
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=str(CONFIG["chroma_path"]))
        _collection = client.get_collection(
            "documents",
            embedding_function=EMBEDDING_FUNCTION,
        )
        debug_log(f"ChromaDB接続: {CONFIG['chroma_path']}")
    return _collection


@mcp.tool()
def search(query: str, top_k: int = 5) -> str:
    """
    架空の野球選手・大堀翔に関する情報を検索する。

    大堀翔のプロフィール、成績、インタビュー、トレーニング、エピソードなどの質問に回答するために使用する。
    ユーザーが大堀翔について質問したら、まずこのツールで関連情報を取得すること。

    Args:
        query: 検索クエリ（例: "大堀翔の成績", "二刀流のトレーニング"）
        top_k: 返す結果数（デフォルト: 5）

    Returns:
        検索結果のテキスト（出典ファイル名付き）
    """
    debug_log(f"search() 呼び出し: query='{query}', top_k={top_k}")

    # 検索実行（クエリをベクトル化 → ChromaDBで類似度検索）
    print("クエリをベクトル化中...", file=sys.stderr)
    debug_log("検索実行中...")
    collection = get_collection()
    results = collection.query(
        query_texts=[f"{E5_QUERY_PREFIX}{query}"],
        n_results=top_k,
    )

    # 結果を整形
    # ChromaDBの検索結果は以下の構造（クエリが1つなので[0]で取り出す）:
    #
    # results = {
    #   "documents": [["野球では9人の選手が...", "野球は2つのチームが..."]],  # テキスト本文
    #   "metadatas": [[{"source": "positions.txt", "chunk_index": 0}, {...}]],  # メタデータ
    #   "distances": [[1.73, 1.80]],  # クエリとの距離（小さいほど類似）
    #   "ids": [["positions.txt_0", "rules.txt_0"]],  # ドキュメントID
    # }
    #
    documents = results["documents"][0] if results["documents"] else []
    metadatas = results["metadatas"][0] if results["metadatas"] else []
    distances = results["distances"][0] if results["distances"] else []

    debug_log(f"検索結果: {len(documents)}件")

    # 結果をテキストに整形
    output_lines = []
    for i, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances)):
        source = meta.get("source", "不明")
        # 距離スコア（小さいほど類似。ChromaDB デフォルトは L2 距離）
        output_lines.append(f"[{i+1}] 出典: {source} (距離: {dist:.2f})")
        output_lines.append(doc)
        output_lines.append("")  # 空行

    if not output_lines:
        return "検索結果が見つかりませんでした。"

    return "\n".join(output_lines)


# サーバー起動
if __name__ == "__main__":
    debug_log("MCPサーバー起動")
    debug_log(f"ChromaDBパス: {CONFIG['chroma_path']}")

    # stdio経由でJSON-RPC通信を開始
    mcp.run()
