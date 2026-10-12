---
title: "必要な環境と Docker の導入"
description: "このプロジェクトの実行と試験は、すべて Docker の Ubuntu 24.04 コンテナ内で行う。 この章で扱うのは、必要なリソースの確認と Docker の導入まで。 プロジェクトのビルドと起動は 動く環境を用意す…"
lang: ja
---

# 必要な環境と Docker の導入

![Alice と Bob、2人の子どもが楽しそうに遊んでいるイラスト](../images/alice-bob.png)

このプロジェクトの実行と試験は、すべて Docker の Ubuntu 24.04 コンテナ内で行う。
この章で扱うのは、必要なリソースの確認と Docker の導入まで。
プロジェクトのビルドと起動は [動く環境を用意する](03-environment.md) で扱う。

> [!TIP]
> **Docker がすでに入っているなら**
>
> [前提条件](#前提条件) でリソースだけ確認し、[動く環境を用意する](03-environment.md) へ進む。
> Docker そのものの説明は [Docker 入門](02-docker-basics.md) にある。

## 前提条件

ホスト側に必要なのは Docker のみ。Python と uv はコンテナ内にある。

| 項目 | 必要量 | 備考 |
|------|-------|------|
| Docker Engine + Compose v2 | — | Docker Desktop でも可 |
| メモリ | **6GB 以上** | 実測ピーク 3.8GB（OS込み・LLM実行時） |
| ディスク | **20GB 程度** | 内訳は下記 |

| 内容 | 容量 |
|------|------|
| `app` イメージ（PyTorch を含む） | 4.3GB |
| `ollama` イメージ | 8.4GB |
| ビルドキャッシュ | 4.4GB |
| ボリューム（埋め込みモデル + LLM + DB） | 1.9GB |

いずれも Ubuntu 24.04（2 vCPU / 8GB）での実測値。
Step 1 から Step 3 までは LLM を使わないため、`ollama` のイメージとモデル
（約 9.8GB）は後回しにできる。

現在の割り当ての確認。

{% raw %}
```bash
docker info --format 'メモリ: {{.MemTotal}}'
df -h /
```
{% endraw %}

## 非力なマシンでは、ここが重い

上の 20GB という数字は、**Step 4（LLM）まで含めたとき**のものである。
重いのは Docker ではなく、LLM をローカルで動かすことによる。

| 要るもの | 量 | 効いてくる場面 |
|---------|-----|--------------|
| `ollama` イメージ | 8.4GB | 最初の取得。回線が細いと、ここで止まる |
| モデル | 1.4GB〜 | 同上 |
| `app` イメージ | 約4GB | PyTorch を含むため |
| メモリ | 6GB 以上 | 推論中 |

さらに、**コンテナ内の推論は CPU で行われる。**
macOS では Apple Silicon の GPU をコンテナに渡せず、Linux でも GPU を使うには
別の設定が要る。1問あたり十数秒かかるのはこのためである。

手元が非力なら、次のように落とすとよい。**Step 3 までは何も落とさずに動く。**

### 1. LLM を使わない範囲で読む

Step 1 から Step 3（ChromaDB・MCP）に LLM は要らない。
`ollama` イメージもモデルも取得せず、`app` だけを起動する。

```bash
docker compose up -d --no-deps app
```

MCP の仕組みはここまでで全部出てくる。**この教材の主題は Step 3 までに収まっている。**

### 2. ホスト側の Ollama を使う

すでに Ollama を入れているなら、8.4GB のイメージを取らずに済む。
Apple Silicon なら GPU が使えるので、速度も上がる。`.env` に書く
（[Ollama を用意する](08-ollama-setup.md)）。

```bash
OLLAMA_HOST=http://host.docker.internal:11434
```

### 3. もっと小さいモデルにする

`qwen3:1.7b` でも重ければ、`qwen3:0.6b`（522MB）がある。
ただし**ツールを選び損ねることが増える。** 質問3種を6回ずつ投げた結果である。

```
qwen3:1.7b    18/18
qwen3:0.6b    13/18
```

> [!WARNING]
> **イメージの取得が進まないことがある**
>
> `ollama` イメージは 8.4GB あり、回線によっては取得に失敗したまま
> 進捗が止まって見えることがある。
> 止まったら `docker compose down` で一度落とし、`docker pull ollama/ollama` を
> 単体で実行して様子を見る。取得さえ済めば、次回からはやり直しは要らない。

## Docker を導入する

### Ubuntu の場合

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-v2 git
sudo usermod -aG docker $USER
```

**`usermod` の結果は再ログインするまで反映されない。** 一度ログアウトして入り直す。
忘れると、次の手順で `permission denied` になる。

導入の確認。

```bash
docker --version
docker compose version
docker run --rm hello-world
```

`Hello from Docker!` が表示されれば完了。`sudo` なしで動作することも、
ここで同時に確認できる。

> [!NOTE]
> **Ubuntu の標準パッケージを使っている**
>
> Ubuntu 24.04 の標準パッケージ（Docker 29.1、Compose 2.40）で
> このプロジェクトが動作することを実測している。
> Docker 公式のリポジトリを追加する方法もあるが、手順が長くなる。

### macOS / Windows の場合

[Docker Desktop](https://www.docker.com/products/docker-desktop/) を導入する。
Compose は同梱されており、追加の作業はない。

## 次へ

Docker が動作したら、[Docker 入門](02-docker-basics.md) へ進む。
コンテナ・イメージ・ボリュームといった語彙を、公開イメージを使った数行の例で確認する。

Docker に慣れているなら、[動く環境を用意する](03-environment.md) へ直接進んでよい。
