# mcp-rag-server

教育目的のMCPプロジェクト。MCPプロトコルの仕組みを学ぶため、クライアントとサーバーの両方を自作する。

## コンセプト

```
┌─────────────────────────────────────────────────────────────┐
│                    MCPクライアント                           │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐ │
│  │ ユーザー入力 │ ──→ │   Ollama    │ ──→ │ ツール判定   │ │
│  └─────────────┘      │  (ローカル   │      └──────┬──────┘ │
│                       │    LLM)     │             │        │
│  ┌─────────────┐      └─────────────┘             │        │
│  │  回答出力   │ ←── 回答生成 ←── 検索結果 ←─────┘        │
│  └─────────────┘                                           │
└─────────────────────────────────────────────────────────────┘
                                │
                          MCPプロトコル
                           (stdio通信)
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                     MCPサーバー                              │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐ │
│  │ ツール定義   │      │  search()   │ ──→ │  ChromaDB   │ │
│  │ (search)    │      │  実行       │ ←── │  クエリ     │ │
│  └─────────────┘      └─────────────┘      └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## この教材が教えること

**MCP をプロトコルレベル・コードレベルで理解する。** これが唯一の目的である。

| 対象 | どこまで扱うか |
|------|--------------|
| **MCP** | **主題。** JSON-RPC のメッセージを1行ずつ組み立てて、通信仕様を理解する |
| ChromaDB | **使えればよい。** API の呼び方が分かればそこで止める |
| 埋め込みモデル | 呼び方だけ。モデルの性質や精度は扱わない |
| Ollama tool calling | LLM がツールを選ぶ仕組みを理解する（Step 4） |
| RAG | 上を積み上げると RAG の形になる、という理解 |

**ChromaDB や埋め込みの深掘りは、この教材の仕事ではない。**
チャンク分割、モデルの比較、距離の分布、精度の改善——どれも実務では重要だが、
MCP の理解には寄与しない。書きたくなったら**書かない。**

## 技術スタック

- **言語**: Python 3.11+
- **LLM**: Ollama (ローカル実行)
- **MCP SDK**: mcp (公式Python SDK)
- **ベクトルDB**: ChromaDB (永続化モード)
- **埋め込み**: `intfloat/multilingual-e5-small`
- **パッケージ管理**: uv

## ディレクトリ構造

```
mcp-rag-server/
├── pyproject.toml
├── mkdocs.yml                # ドキュメントサイト設定（mkdocs-material）
├── src/
│   ├── client/
│   │   ├── __init__.py
│   │   └── main.py           # MCPクライアント + Ollama連携
│   └── server/
│       ├── __init__.py
│       ├── main.py           # MCPサーバー本体
│       ├── indexer.py        # テキストファイルのインデックス処理
│       └── config.py         # 設定管理
├── data/
│   └── documents/            # インデックス対象の.txtファイル配置場所
├── tests/                    # pytest（chromadb/indexer/server/client/統合）
├── tools/
│   └── query_chromadb.py     # ChromaDB単体で検索を試すスクリプト
├── docs/                     # 日本語ドキュメント（GitHub Pagesで公開）
│   └── refs/                 # 各ソースファイルの詳細リファレンス
└── chroma_db/                # ChromaDB永続化ディレクトリ（gitignore）
```

英語版は `docs/en/` に同居し、`docs/ja/` からの翻訳で生成する。
編集するのは日本語版だけで、英語版は翻訳し直す。
図も同様に、`docs/images/` が正で `docs/images/en/` が英語版である。

## コンポーネント詳細

### 1. MCPサーバー (`src/server/`)

ツールを3つ提供する。

| ツール | 引数 | 何をするか |
|-------|------|-----------|
| `search` | `query`, `top_k=5` | 意味の近い文書を探す |
| `list_documents` | 無し | ファイル名を一覧する |
| `get_document` | `name` | ファイル1つを丸ごと返す |

**3つあるのは教材としての判断である。** 1つだと `tools/list` が配列である意味も、
LLM が「選ぶ」という動作も見せられない。`inputSchema` が
「必須＋既定値つき」「引数なし」「必須1つ」と3通りに分かれるようにしてある。

#### ツール定義

MCP SDK v2 の `MCPServer` を使い、`@mcp.tool()` で関数を登録するだけでツールになる。
（v1 の `FastMCP` は廃止された。v1 と v2 に互換性はない）

```python
from mcp.server.mcpserver import MCPServer

mcp = MCPServer("rag-search-server")

@mcp.tool()
def search(query: str, top_k: int = 5) -> str:
    """
    架空のカフェ「The Wandering Kettle」に関する情報を検索する。

    Args:
        query: 検索クエリ
        top_k: 返す結果数

    Returns:
        検索結果のテキスト（出典ファイル名・距離スコア付き）
    """
```

- 戻り値は整形済みの1本のテキスト（構造化データではない）。そのままLLMに渡せる形にしている
- ChromaDBへの接続は初回の `search()` 呼び出しまで遅延させる（`get_collection()`）
- stdout は JSON-RPC 通信で使うため、ログは必ず stderr に出す

#### 初期化処理（`indexer.py`）

1. `data/documents/` 内の `.txt` ファイルを走査
2. ChromaDBにベクトル化して保存（**1ファイルが1件**。分割はしない）

埋め込みモデル `multilingual-e5-small` の作法に合わせ、prefix を付ける。

- インデックス時: `passage: ` を各文書の先頭に付与
- 検索時: `query: ` をクエリの先頭に付与

### 2. MCPクライアント (`src/client/`)

LLMと連携し、ユーザーとの対話を管理する。
LLM は Ollama のみ。モックは置かない（**何を学ぶかがぼやけるため**）。

#### 処理フロー

```python
# 1. MCPサーバーを子プロセスとして起動し、接続
async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()

        # 2. ツール一覧を取得し、Ollama形式に変換
        tools_result = await session.list_tools()
        ollama_tools = mcp_tools_to_ollama_format(tools_result.tools)

        # 3. 質問とツール一覧をLLMに送信
        response = call_llm(user_input, tools=ollama_tools)

        # 4. ツール呼び出しが必要か判定
        if response["message"].get("tool_calls"):
            # 5. MCPサーバーにツール実行を依頼
            result = await session.call_tool("search", func_args)
            search_result = result.content[0].text

            # 6. 検索結果をプロンプトに埋め込み、LLMで回答を生成
            answer = generate_answer(context=search_result, question=user_input)
```

`role: "tool"` のメッセージで会話履歴に戻す方式ではなく、検索結果をプロンプトに直接埋め込む。
処理の流れが読んで分かることを優先した、教育目的の割り切り。

## 設定

| 設定項目 | 環境変数 | デフォルト値 |
|---------|---------|-------------|
| ドキュメントフォルダ | `RAG_DOCUMENTS_PATH` | `./data/documents` |
| ChromaDB保存先 | `RAG_CHROMA_PATH` | `./chroma_db` |
| Ollamaモデル | `OLLAMA_MODEL` | `qwen3:1.7b` |
| デバッグ出力 | `RAG_DEBUG` | 未設定（無効） |

`RAG_DEBUG` は `1` / `true` / `yes` で有効になる（`config.py` ではなく `main.py` で直接読む）。
埋め込みモデルは環境変数ではなく `config.py` に直書き。

## 開発コマンド

**実行と試験は Docker の Ubuntu コンテナで行う**（`docs/ja/03-environment.md` 参照）。

```bash
docker compose up -d
docker compose exec app bash
```

コンテナに入った後は普通の Ubuntu として扱える。
`uv sync` がプロジェクトを editable install するので、**`PYTHONPATH` は不要**。

```bash
# 依存関係インストール
uv sync

# Step 1（RAG だけ。MCP も LLM も不要、事前準備も要らない）
uv run python steps/01_chromadb.py

# ドキュメントのインデックス作成（初回とデータ差し替え時）
uv run python -m server.indexer     # または rag-index

# クライアント起動（Ollama が要る）
uv run python -m client.main        # または rag-client

# テスト
uv run pytest

# ChromaDBの検索結果だけを確認（MCP・LLMを介さない）
uv run python tools/query_chromadb.py
```

## デバッグ方法

### MCP Inspector での動作確認

MCPサーバー単体の動作を確認する場合:

```bash
npx @modelcontextprotocol/inspector uv run python -m server.main
```

### JSON-RPC 通信の可視化

`RAG_DEBUG=1` を付けると、`initialize` → `tools/list` → `tools/call` のメッセージが表示される。

```bash
RAG_DEBUG=1 uv run python -m client.main
```

## 依存パッケージ

```toml
[project]
dependencies = [
    "mcp>=2.0.0",     # v2 で FastMCP が廃止され MCPServer になった
    "chromadb>=0.4.0",
    "ollama>=0.4.0",
    "sentence-transformers>=2.2.0",
    "torch>=2.0.0",   # CPU版をPyTorch専用インデックスから取得
]

[project.scripts]
rag-index = "server.indexer:main"
rag-client = "client.main:main"

[dependency-groups]
dev = ["pytest>=9.0.2", "pytest-asyncio>=1.3.0"]
```

`uv.lock` は追跡する。環境ごとに解決結果が変わると、教材で
「手元では動くのに動かない」が起きるため。

## 前提条件

1. **Python 3.11+**: uv でインストール管理

2. **Ollama**: Step 4 で必須。モデルをダウンロードしておく。
   ```bash
   ollama pull qwen3:1.7b
   ```

3. 初回起動時、埋め込みモデル（約470MB）が Hugging Face から自動ダウンロードされる。

## サンプルデータ

`data/documents/` には架空のカフェ「The Wandering Kettle」の資料7ファイルを置いている
（menu_drinks / menu_food / hours_access / faq / allergens / staff_handbook / story）。

- **架空**なので、LLM は検索なしでは答えられない。RAG が効いているか一目で分かる
- **日常語彙**なので「意味で引ける」実感が得やすい（数値の羅列だと分かりにくい）
- **英語のみ**。日本語のクエリでも引ける（埋め込みモデルが多言語のため）

埋め込みモデルを英語専用に替えると、日本語クエリで引けなくなる。
`multilingual-e5-small` は意図的な選択なので、後から「単純化」して壊さないこと。

## 言語の使い分け

**コードは完全に英語の成果物とする。** 説明は日本語だが、それはドキュメントが担う。

| 対象 | 言語 |
|------|------|
| `data/documents/` の資料 | 英語 |
| ソースコードのコメント・docstring | **英語** |
| 実行時の表示（print の文言） | **英語** |
| LLM やプロトコルに渡る文字列 | 英語 |
| `docs/ja/` | 日本語（これが正） |
| `docs/en/` | 英語（`docs/ja` からの翻訳） |

コードを1つの英語成果物にしておくと、日英どちらのドキュメントからも同じコードを
そのまま引用できる。英語圏の読者が実行しても日本語が出てこない。

日本語で質問しても検索自体は動く（埋め込みモデルが多言語のため）が、
**言語を判定して切り替える処理はコードに入れない**。
MCP や RAG と無関係な分岐が増えると、処理の流れが追いにくくなる。

## ドキュメントの書き方

**明瞭かつ簡潔に。短いほどよい。ただし意味が曖昧になる手前まで。**

書くかどうかは、次の一問で決める。

> **それを知らないと、ソースコードが読めないか？**

読めるなら書かない。正しくても、実測してあっても、面白くても、書かない。

### 削る基準

- 同じことを二度書かない。前置き・言い換え・まとめの重複を削る
- 図に描いたことを本文で繰り返さない。コードから読めることを文章にしない
- 他章にあるなら参照1行で済ませる
- 使っていない引数・選ばなかった選択肢・背景知識は書かない
- 数値の分布や傾向は書かない。**動かすのに要らない**

### 書き方

- である調。です・ます調と「〜してください」は使わない
- 初出の語はその場で定義する。読者がまだ知らない語で説明を始めない
- 前方参照を避ける。必要なものはその場に置く
- 表は2つ以上の軸で比べるときだけ使う。1文で足りるなら表にしない
  - 列ごとに「これが無いと読めないか」を確かめる。形が整っているだけの表は消す
- 見出しは対象と動作を含める（「入れる」ではなく「文書を登録する」）

### ソースコードの載せ方

**そのまま貼らない。説明したい筋だけを残して整形する。**

- ログ出力、デバッグ用の分岐、まれな条件の `if`、エラー処理は消す
- 引数は省いてよい（`...`）。長い式は短い変数名に置き換えてよい
- 2つを比べるときは**名前と構造を揃える**。差が1行に見えるまで削る
- 簡略化したものは、そうと分かる形で断る（「要点だけを抜き出した形」など）

コマンドの**出力**は別で、これは加工しない（下記「正確さ」）。

### 正確さ

- 数値・コマンド出力・図中の値は、実行して確かめてから書く
- 出力の引用は省略しない。省略するなら省略したと明示する
- 図は実測か模式かを明示する。両者を混ぜない
- 開発機の情報（ホスト名・ユーザ名・固有パス・認証情報）は書かない

## コーディング規約

- 型ヒントを必須とする
- docstringはGoogle形式
- ログは `print()` で出力する（`logging` は使わない。教育目的でシンプルさを優先）
  - MCPサーバー側は stdout が JSON-RPC 通信に使われるため、**必ず stderr に出す**

## 教育目的の設計方針

このプロジェクトは**初心者がコードを読んで動作を理解する**ことが最優先目標。

### 基本原則: 最小限のシンプルさ

- **これ以上削ったら意味がなくなる**というレベルまでシンプルに
- 本格的な実装より「動きが見える」ことを重視
- 1ファイルで完結できるなら1ファイルに
- クラスより関数、関数よりベタ書きを優先
- 抽象化・再利用性・拡張性は考えない

### コードの書き方

- 各処理が何をしているか、コメントで説明する（言語は上表のとおり英語）
- 平易な英語で書く。凝った語彙より、読んで意味が取れることを優先する
- エラー処理は最小限（ハッピーパスのみ）
- 設定は直書き or 最小限の変数で
- pytestのフィクスチャ等の高度な機能は避ける

### チャンク分割はしない

文書は**1ファイル＝1件**でそのまま ChromaDB に入れる。分割（チャンク化）は
実務では有効だが、このプロジェクトの目的は MCP をプロトコルレベルで理解すること
であり、分割の巧拙は MCP とも ChromaDB の API とも関係がない。

資料は7ファイル・1万字と小さく、分割しなくても正しく引ける（実測で確認済み）。
**「精度のために」と称して分割を持ち込まないこと。**

### ファイル構成

```
良い例: 50行で動作が一目瞭然
悪い例: 200行で本格的だが読むのに時間がかかる
```

### テストの書き方

```python
# 良い例: 何をしているか一目でわかる
def test_chromadb_search():
    # 1. DBを作る
    client = chromadb.Client()
    collection = client.create_collection("test")

    # 2. データを入れる
    collection.add(ids=["1"], documents=["Dogs are welcome on the terrace"])

    # 3. 検索する
    results = collection.query(query_texts=["犬"], n_results=1)

    # 4. 結果を確認
    assert "Dogs" in results["documents"][0][0]
```
