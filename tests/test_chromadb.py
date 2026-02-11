"""
ChromaDBの動作確認テスト

このテストで確認すること:
1. ドキュメントを追加できる
2. ベクトル検索（類似検索）ができる
3. メタデータ（ファイル名など）を保存・取得できる
"""

import chromadb
from pathlib import Path


def test_basic_add_and_search():
    """ChromaDBにデータを入れて検索できることを確認"""

    # === 1. ChromaDBクライアントを作成 ===
    # メモリモード（永続化しない）でシンプルに
    client = chromadb.Client()

    # === 2. コレクション（テーブルのようなもの）を作成 ===
    collection = client.create_collection(name="test_baseball")

    # === 3. ドキュメントを追加 ===
    # ChromaDBが自動的にテキストをベクトル化してくれる
    collection.add(
        ids=["doc1", "doc2", "doc3"],  # 一意のID
        documents=[
            "大堀翔は投手と打者の二刀流選手です。",
            "野球は9人対9人で行うスポーツです。",
            "夏の全国高校野球大会は8月に開催される。",
        ],
        metadatas=[  # 付加情報（ファイル名など）
            {"source": "player.txt"},
            {"source": "rules.txt"},
            {"source": "tournament.txt"},
        ],
    )

    # === 4. 類似検索を実行 ===
    # 「二刀流について」で検索すると、大堀の文が見つかるはず
    results = collection.query(
        query_texts=["二刀流の選手について教えて"],
        n_results=2,  # 上位2件を取得
    )

    # === 5. 結果を確認 ===
    # 検索結果の構造: results["documents"][0] = 1つ目のクエリの結果リスト
    print("検索結果:")
    print(f"  1位: {results['documents'][0][0]}")
    print(f"  2位: {results['documents'][0][1]}")

    # 「大堀」が含まれる結果が返ってくることを確認
    top_result = results["documents"][0][0]
    assert "大堀" in top_result


def test_get_filename_from_metadata():
    """検索結果からファイル名（出典）を取得できることを確認"""

    client = chromadb.Client()
    collection = client.create_collection(name="test_metadata")

    # ドキュメント追加時にメタデータも一緒に保存
    collection.add(
        ids=["1"],
        documents=["打率は安打数を打数で割った値です。"],
        metadatas=[{"source": "stats.txt", "topic": "指標"}],
    )

    # 検索
    results = collection.query(query_texts=["打率とは"], n_results=1)

    # メタデータを取得
    metadata = results["metadatas"][0][0]
    print(f"出典ファイル: {metadata['source']}")
    print(f"トピック: {metadata['topic']}")

    assert metadata["source"] == "stats.txt"
    assert metadata["topic"] == "指標"


def test_search_real_text_files():
    """data/documents/ にある実際のファイルを読み込んで検索"""

    # テキストファイルの場所
    docs_dir = Path(__file__).parent.parent / "data" / "documents"

    if not docs_dir.exists():
        print(f"スキップ: {docs_dir} が存在しません")
        return

    # テキストファイルを読み込む
    txt_files = list(docs_dir.glob("*.txt"))
    if not txt_files:
        print("スキップ: テキストファイルがありません")
        return

    print(f"見つかったファイル: {[f.name for f in txt_files]}")

    # ChromaDBに登録
    client = chromadb.Client()
    collection = client.create_collection(name="real_docs")

    for i, txt_file in enumerate(txt_files):
        content = txt_file.read_text(encoding="utf-8")
        collection.add(
            ids=[f"doc_{i}"],
            documents=[content],
            metadatas=[{"source": txt_file.name}],
        )

    print(f"登録したドキュメント数: {collection.count()}")

    # 検索テスト
    results = collection.query(query_texts=["大堀翔について"], n_results=1)

    print(f"検索結果: {results['metadatas'][0][0]['source']}")
    assert collection.count() == len(txt_files)
