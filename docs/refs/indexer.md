# indexer.py — インデックス作成

対応ソース: `src/server/indexer.py`（158行）

## 概要

テキストファイルを読み込み、チャンクに分割して ChromaDB に保存します。

## アルゴリズム

1. 指定フォルダ内の `.txt` ファイルを全て読み込む
2. 各テキストを `chunk_size` 文字ごとに分割（`overlap` 文字の重複あり）
3. ChromaDB に E5 プレフィックス付きで保存（メタデータに出典ファイル名を記録）

## 定数リファレンス

### `EMBEDDING_FUNCTION`

```python
EMBEDDING_FUNCTION = SentenceTransformerEmbeddingFunction(
    model_name=CONFIG["embedding_model"]
)
```

ChromaDB に渡す埋め込み関数です。`SentenceTransformerEmbeddingFunction` は ChromaDB が提供するラッパーで、テキストを渡すと自動でベクトルに変換してくれます。

### `E5_DOCUMENT_PREFIX`

```python
E5_DOCUMENT_PREFIX = "passage: "
```

E5 モデルの規約で、保存する文書には `"passage: "` を付けます（詳しくは [RAG 解説](../03-rag-explained.md) を参照）。

## 関数リファレンス

### `load_text_files(documents_path)`

```python
def load_text_files(documents_path: Path) -> list[dict]
```

| 引数 | 型 | 説明 |
|------|-----|------|
| `documents_path` | `Path` | テキストファイルのフォルダ |

**戻り値:** `[{"filename": "xxx.txt", "content": "..."}, ...]`

指定フォルダ内の `.txt` ファイルを全て読み込みます。`glob("*.txt")` で `.txt` ファイルだけを取得します。

---

### `split_into_chunks(text, chunk_size, overlap)`

```python
def split_into_chunks(text: str, chunk_size: int, overlap: int) -> list[str]
```

| 引数 | 型 | 説明 |
|------|-----|------|
| `text` | `str` | 分割対象のテキスト |
| `chunk_size` | `int` | 1チャンクの文字数 |
| `overlap` | `int` | チャンク間の重複文字数 |

**戻り値:** チャンクのリスト

テキストを `chunk_size` 文字ごとに分割します。次のチャンクの開始位置を `overlap` 文字ぶん手前に戻すことで、チャンク間に重複区間を作ります。

**例:** 1000文字のテキスト、chunk_size=400、overlap=80 の場合

```
チャンク1: text[0:400]
チャンク2: text[320:720]     ← 400-80=320 から開始
チャンク3: text[640:1000]    ← 720-80=640 から開始
```

---

### `index_documents(documents_path, chroma_path, chunk_size, chunk_overlap, collection_name)`

```python
def index_documents(
    documents_path: Path,
    chroma_path: Path,
    chunk_size: int,
    chunk_overlap: int,
    collection_name: str = "documents",
) -> int
```

| 引数 | 型 | デフォルト | 説明 |
|------|-----|-----------|------|
| `documents_path` | `Path` | — | テキストファイルのフォルダ |
| `chroma_path` | `Path` | — | ChromaDB 保存先 |
| `chunk_size` | `int` | — | チャンクサイズ |
| `chunk_overlap` | `int` | — | オーバーラップ |
| `collection_name` | `str` | `"documents"` | コレクション名 |

**戻り値:** インデックスしたチャンク数

全体を統括する関数です。処理の流れ:

**ステップ 1: テキスト読み込み**
```python
documents = load_text_files(documents_path)
```

**ステップ 2: ChromaDB 初期化**
```python
client = chromadb.PersistentClient(path=str(chroma_path))

# 既存のコレクションがあれば削除して新規作成
existing = [c.name for c in client.list_collections()]
if collection_name in existing:
    client.delete_collection(collection_name)

collection = client.create_collection(name=collection_name, embedding_function=EMBEDDING_FUNCTION)
```

`PersistentClient` はデータをディスクに永続化するモードです。
既存データがあれば削除して最初から作り直します（毎回クリーンな状態にするため）。

**ステップ 3: チャンク分割と保存**
```python
for doc in documents:
    chunks = split_into_chunks(doc["content"], chunk_size, chunk_overlap)
    for i, chunk in enumerate(chunks):
        chunk_id = f"{doc['filename']}_{i}"
        collection.add(
            ids=[chunk_id],
            documents=[f"{E5_DOCUMENT_PREFIX}{chunk}"],
            metadatas=[{"source": doc["filename"], "chunk_index": i}],
        )
```

各チャンクに一意の ID（`"profile.txt_0"`, `"profile.txt_1"` など）を付けて ChromaDB に保存します。
`documents` に渡したテキストは ChromaDB が自動でベクトル化します。
`metadatas` には出典ファイル名を記録し、検索結果に「出典: profile.txt」と表示できるようにします。
