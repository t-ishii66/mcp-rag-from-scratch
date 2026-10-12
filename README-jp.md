![MCP RAG from scratch](docs/images/top.png)

# MCP RAG from scratch

[English](README.md) · **日本語**

**MCP と RAG を自分で書いて、仕組みを理解する**ためのハンズオン教材です。

MCP 対応のツールを使ったことはあっても、中で何が起きているかは見えません。
このプロジェクトでは、クライアントもサーバーも自分で書きます。
JSON-RPC のメッセージを1行ずつ手で組み立てるところまでやります。

すべてローカルで完結し、API キーは不要です。

---

## ドキュメント

| # | ページ | 内容 |
|---|-------|------|
| 1 | [必要な環境と Docker の導入](docs/ja/01-setup.md) | 必要なリソースの確認と Docker の導入 |
| 2 | [Docker 入門](docs/ja/02-docker-basics.md) | コンテナ・イメージ・ボリューム・Compose。慣れていれば飛ばせる |
| 3 | [動く環境を用意する](docs/ja/03-environment.md) | 2つのコンテナ、データの置き場所、日常の操作、動作確認 |
| 4 | [ChromaDB を動かす](docs/ja/04-chromadb.md) | Step 1 のコードを読み、動かす |
| 5 | [データベースを作り、検索関数を用意する](docs/ja/05-chromadb-persist.md) | ディスクに作り置きし、`search()` を用意する |
| 6 | [MCP を生の JSON-RPC で話す](docs/ja/06-mcp-protocol.md) | Step 2。プロトコルを1行ずつ見る |
| 7 | [MCP を SDK で書く](docs/ja/07-mcp-sdk.md) | Step 3。サーバーとクライアントをコードで書く |
| 8 | [Ollama を用意する](docs/ja/08-ollama-setup.md) | モデルの取得と、単体での動作確認 |
| 9 | [MCP と Ollama の関係](docs/ja/09-mcp-and-ollama.md) | 全体の構造。LLM がツールを選ぶ仕組み |
| 10 | [RAG を完成させる](docs/ja/10-rag.md) | Step 4。LLM を載せて全体が繋がる |
| 11 | [完成版を対話で動かす](docs/ja/11-interactive-client.md) | `src/` の対話クライアントを動かし、全体を振り返る |

1 は Docker を入れるところまで。2 は Docker そのものの入門で、
このプロジェクトは出てきません。**Docker に慣れていれば飛ばせます。**

3 で環境を用意し、`pytest` が通るところまで確かめます。

4 と 5 が ChromaDB です。**MCP を読むのに必要な範囲で止めてあります。**
5 まで読むと検索の側が完結し、MCP は Step 2 から始まります。

6 と 7 が MCP の中心です。8 から 10 で LLM を載せ、11 で対話にします。

---

## 動かすコード

章と並行して、段階ごとに**独立して動く1ファイル**を用意しています。
読みながら、対応する Step を動かしてください。

| Step | ファイル | 作るもの | LLM |
|------|---------|---------|-----|
| 1 | `steps/01_chromadb.py` | **ChromaDB** — 文書を入れて、質問に近いものを取り出す | 不要 |
| 2 | `steps/02_mcp_raw.py` | **MCP** — 生の JSON-RPC で、その検索を別プロセスから呼ぶ | 不要 |
| 3 | `steps/03_mcp_sdk.py` | **MCP** — 同じことを公式 SDK で書く | 不要 |
| 4 | `steps/04_rag.py` | **RAG** — 取り出した文書を LLM に渡して答えを書かせる | 必要 |


---

## 動かし方

実行と試験は Docker の Ubuntu コンテナで行います。

```bash
docker compose up -d
docker compose exec app uv run python steps/01_chromadb.py
```

環境の用意、Ollama の扱い、困ったときの対処は
**[必要な環境と Docker の導入](docs/ja/01-setup.md)** を参照してください。
Docker そのものに不慣れなら、**[Docker 入門](docs/ja/02-docker-basics.md)** が先にあります。

---

## 何を検索するのか

`data/documents/` にある、架空のカフェ **The Wandering Kettle** の資料7ファイルです。

```
allergens.txt      faq.txt           hours_access.txt
menu_drinks.txt    menu_food.txt     staff_handbook.txt
story.txt
```

メニュー、営業時間、FAQ、アレルギー情報、スタッフ手引き、店の成り立ち。

実在しない店にしているのは、LLM が学習済みの知識で答えてしまうと
検索が効いているのか判別できなくなるからです。

データは英語ですが、**日本語で質問しても引けます**。
多言語対応の埋め込みモデルを使っているためで、これ自体が
「ベクトル検索はキーワード一致ではない」ことの分かりやすい実演になっています。

```bash
docker compose exec app uv run python tools/query_chromadb.py
```

```
query> 犬を連れて行ってもいいですか？

--- Search results (1 items) ---
  [1] distance=0.2449  source=faq.txt
      CAN I STAY AND WORK?

The Wandering Kettle - Questions We Get Asked
...
```

日本語で聞いて、英語の `faq.txt` が引けています。
**1ファイルが1件**なので、返るのはファイル全体です。犬の話はこの中にあります。

`data/documents/` の `.txt` を差し替えれば、そのまま別用途の検索ツールになります。

---

## 技術スタック

| カテゴリ | 使うもの |
|---------|---------|
| 言語 | Python 3.11+ |
| MCP | `mcp` 公式 Python SDK v2 |
| ベクトル DB | ChromaDB |
| 埋め込みモデル | `intfloat/multilingual-e5-small` |
| LLM | Ollama（Step 4 のみ） |
| パッケージ管理 | uv |
| 実行環境 | Docker (Ubuntu 24.04) |

---

## テスト

```bash
docker compose exec app uv run pytest
```

Ollama がなくても全て通ります。
