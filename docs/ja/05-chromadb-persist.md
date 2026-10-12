# データベースを作り、検索関数を用意する

![紙の船を浮かべて遊ぶ Alice と Bob](../images/alice-bob-paper-boats.png)

前章のデータベースはメモリ上にあった。実行が終われば消えるので、
起動するたびに7ファイルをベクトル化し直していた。

ディスクに作り置きすれば、その初期化が要らなくなる。
別のプログラムから開くこともできる。

この章でやることは2つ。

1. ディスク（コンテナ内の `/opt/chroma_db`）にデータベースを作る
2. **文字列を受け取って文字列を返す検索関数**を用意する

## メモリからディスクへ — 変わるのは1行

Step 1 はこうだった。

```python
def get_collection():
    client = chromadb.Client()                    # メモリ上。終了すれば消える
    return client.create_collection(name="cafe")
```

ディスクに置くには、クライアントの種類を変えるだけである。

```python
def get_collection():
    client = chromadb.PersistentClient(path=chroma_path)   # ← ここだけが違う
    return client.create_collection(name="documents")
```

（要点だけを抜き出した形。実際のコードでは、作る側が `indexer.py`、
検索する側が `main.py` に分かれている）

## データベースを作る

```bash
docker compose exec app uv run python -m server.indexer
```

```
=== Indexing ===
Documents: /workspace/data/documents
ChromaDB:  /opt/chroma_db

[1] Reading the text files
  read: staff_handbook.txt (1693 chars)
  read: faq.txt (1642 chars)
  ...
  -> 7 files read

[2] Opening ChromaDB
  created collection 'documents'
  embedding model: intfloat/multilingual-e5-small

[3] Indexing
  staff_handbook.txt: 1693 chars
  ...

=== Done: 7 documents indexed ===
```

7 件。Step 1 と同じで、**1ファイルが1件**である。

**このコマンドは1回だけ実行する。** 作ったものはディスクに残るので、
次からは検索するだけでよい。`data/documents/` を書き換えたときに、また実行する。

> [!NOTE]
> **作り直し**
>
> ChromaDB データベースの作り直しは次のコマンドを実行する。
>
> ```bash
> docker compose exec app sh -c 'rm -rf /opt/chroma_db/*'
> docker compose exec app uv run python -m server.indexer
> ```

### 保存先

`/opt/chroma_db` に置いている。プロジェクト直下ではなく、コンテナ内の別の場所である。

`docker-compose.yml` でここを**名前付きボリューム**にしている。

```yaml
services:
  app:
    volumes:
      - .:/workspace               # Edits on the host show up in the container
      - chroma-db:/opt/chroma_db   # Keep ChromaDB outside /workspace
    environment:
      RAG_CHROMA_PATH: /opt/chroma_db

volumes:
  chroma-db:
```

`/workspace` はホストのプロジェクトをそのまま見せている（バインドマウント）。
一方 `chroma-db` は Docker が管理する領域で、ホストのファイルツリーには現れない。


保存先はコードに直書きせず、`RAG_CHROMA_PATH` で渡している。

```bash
docker compose exec app ls /opt/chroma_db
```

```
a33eb2fc-516c-47ce-a4c0-3b3cd66ec7ce
chroma.sqlite3
```

`chroma.sqlite3` が本文とメタデータ、UUID のディレクトリがベクトルの索引である。

## 検索関数を用意する

`src/server/main.py` に、検索する関数がある。

```python
def search(query: str, top_k: int = 5) -> str:
    collection = get_collection()
    results = collection.query(
        query_texts=[f"{E5_QUERY_PREFIX}{query}"],
        n_results=top_k,
    )

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    output_lines = []
    for i, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances)):
        source = meta.get("source", "unknown")
        output_lines.append(f"[{i+1}] source: {source} (distance: {dist:.2f})")
        output_lines.append(doc)
        output_lines.append("")

    return "\n".join(output_lines)
```

`get_collection()` は**作り置きされたコレクションを開く**。
`create_collection()` ではない。検索する側は作らない。

1件につき3行を `output_lines` に積む。見出し、本文、空行である。
`top_k=2` で引くと、こうなる。

```python
output_lines = [
    '[1] source: hours_access.txt (distance: 0.16)',
    'passage: The Wandering Kettle - Hours and Directions\n\nWHEN WE ARE OPEN\n\n...',
    '',
    '[2] source: staff_handbook.txt (distance: 0.18)',
    'passage: The Wandering Kettle - Notes for Staff\n\nOPENING\n\nArrive forty...',
    '',
]
```

最後に `"\n".join()` で1本の文字列にする。

やっていることは前章と同じ `query()` の呼び出しで、違いは**戻り値の形**である。

```
search(query: str, top_k: int = 5) -> str
```

**文字列を受け取り、整形した文字列を1本返す。** 辞書も配列も返さない。

整形まで済ませてあるので、**呼ぶ側は結果の構造を知らなくてよい**。
二重のリストをたどる必要も、距離を丸める必要もない。
文字列を受け取って文字列を返す関数は、そのまま他のプログラムから呼べる部品になる。

返るのはこういう文字列である。

```
[1] source: hours_access.txt (distance: 0.16)
passage: The Wandering Kettle - Hours and Directions

WHEN WE ARE OPEN

Monday: 8:00 to 18:00
Tuesday: 8:00 to 18:00
...

[2] source: staff_handbook.txt (distance: 0.18)
...
```

## 検索を試す

関数を通さず、ChromaDB を直接引くツールがある。

```bash
docker compose exec app uv run python tools/query_chromadb.py
```

```
Using the existing ChromaDB: /opt/chroma_db
--------------------------------------------------
Collections: ['documents']
Collection in use: documents (7 items)
--------------------------------------------------
Enter a search query (type quit to exit)

query> opening hours

--- Search results (1 items) ---
  [1] distance=0.1608  source=hours_access.txt
      WHEN WE ARE OPEN
      The Wandering Kettle - Hours and Directions
      ...
```

`Using the existing ChromaDB` と出ている。作り直していない。
ベクトル化するのは、これから入力するクエリだけである。

既定は1件。末尾に ` /数字` を付けると増える（`opening hours /3`）。
`quit` で終了する。

### 「該当なし」は返ってこない

```
query> quantum physics

--- Search results (1 items) ---
  [1] distance=0.2254  source=faq.txt
```

カフェの資料に量子力学の話はない。それでも**何かが必ず1位になる**。
ベクトル検索は「一番近いものを返す」だけで、「十分に近いか」は判断しない。

この性質は Step 4 で LLM を載せるときに効いてくる。
関係のない文書を渡されても、LLM は何か答えようとする。

## 自分のデータに差し替える

`data/documents/` に入っているカフェの7ファイルを、自分の `.txt` に入れ替える。
ホスト側で消して置くだけでよい。バインドマウントなので、そのままコンテナから見える。

```bash
# 1. ホスト側でカフェの資料を消し、自分のファイルを置く
rm data/documents/*.txt
cp ~/my-notes/*.txt data/documents/

# 2. 古いデータベースを消して、作り直す
docker compose exec app sh -c 'rm -rf /opt/chroma_db/*'
docker compose exec app uv run python -m server.indexer

# 3. 引いてみる
docker compose exec app uv run python tools/query_chromadb.py
```

`.txt` であれば中身は何でもよい。日本語でも引ける。

## ここまでで分かったこと

- メモリとディスクの違いは `Client()` か `PersistentClient(path=...)` かだけ
- 作る側は `create_collection()`、検索する側は `get_collection()`
- 検索関数は**文字列を受け取って文字列を返す**。呼ぶ側は中の構造を知らなくてよい
- 接続は初回の呼び出しまで遅らせる

**検索の側はここで完結する。** 次の Step 2 では、
いま用意した `search()` を**別プロセスから呼ぶ**。
検索の中身は変わらない。変わるのは呼び出し方だけである。
