# MCP RAG from scratch

**MCP と RAG を「完全自作」して仕組みを理解する**、ハンズオン型の学習プロジェクトです。

すべてローカルで完結し、API キーは不要です。
プロジェクトの詳細は [GitHub リポジトリの README](https://github.com/t-ishii66/mcp-rag-from-scratch) を参照してください。

## ドキュメント

| # | ドキュメント | 内容 |
|---|-------------|------|
| 1 | [環境構築ガイド](01-setup.md) | uv・Ollama のインストールからプロジェクトの起動まで |
| 2 | [MCP プロトコル解説](02-mcp-explained.md) | MCP とは何か、JSON-RPC 通信の仕組み、ツール呼び出しの流れ |
| 3 | [RAG 解説](03-rag-explained.md) | RAG の概念、ベクトル検索、チャンク分割、埋め込みモデル |
| 4 | [コード解説](04-code-walkthrough.md) | ソースファイルの概要と、各ファイルの[詳細リファレンス](refs/config.md) |
| 5 | [チュートリアル](05-tutorial.md) | 実際に手を動かして動作確認する手順書 |

## おすすめの読み方

1. **[環境構築ガイド](01-setup.md)** で動かせる状態にする
2. **[チュートリアル](05-tutorial.md)** で実際に動かして全体の流れを体験する
3. **[MCP プロトコル解説](02-mcp-explained.md)** と **[RAG 解説](03-rag-explained.md)** で背景知識を固める
4. **[コード解説](04-code-walkthrough.md)** でソースコードを深く理解する

すでに MCP や RAG を知っている方は、[コード解説](04-code-walkthrough.md) から読み始めても構いません。
