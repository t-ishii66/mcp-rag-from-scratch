"""
MCPサーバー

ChromaDBを使った検索ツールを提供する。
JSON-RPC 2.0プロトコルでstdio通信を行う。

デバッグモード:
  RAG_DEBUG=1 で起動すると、JSON-RPC通信の内容をstderrに出力する。
"""

import sys
import os
import chromadb
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


@mcp.tool()
def search(query: str, top_k: int = 5) -> str:
    """
    ChromaDBから関連テキストを検索する。

    Args:
        query: 検索クエリ（例: "大谷翔平の成績"）
        top_k: 返す結果数（デフォルト: 5）

    Returns:
        検索結果のテキスト（出典ファイル名付き）
    """
    debug_log(f"search() 呼び出し: query='{query}', top_k={top_k}")

    # ChromaDBに接続
    chroma_path = str(CONFIG["chroma_path"])
    debug_log(f"ChromaDB接続: {chroma_path}")

    client = chromadb.PersistentClient(path=chroma_path)
    collection = client.get_collection("documents")

    # 検索実行
    debug_log("検索実行中...")
    results = collection.query(
        query_texts=[query],
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
        # 類似度スコア（距離が小さいほど類似）
        score = 1 - dist  # 0〜1の類似度に変換（概算）
        output_lines.append(f"[{i+1}] 出典: {source} (類似度: {score:.2f})")
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
