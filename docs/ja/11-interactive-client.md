# 完成版を対話で動かす

終章である。`steps/` の4本は、どれも質問が1つ埋め込まれたスクリプトだった。
`src/` には、**同じ仕組みを対話形式でやる完成版**がある。

自分で質問しながら動かし、中で何が起きているかを最後にもう一度見る。

## 対話で動かす

ここからが完成版の `src/client/main.py` である。
流れは [9章のシーケンス図](09-mcp-and-ollama.md#質問1つに何が起きるか)のとおりで、
それをそのまま対話にしたものである。

```bash
docker compose exec app uv run python -m client.main
```

```
=== MCP RAG client ===
LLM: qwen3:1.7b
Type 'quit' to leave.

[1] Connected to the MCP server
[2] Tools reported by the server: ['search', 'list_documents', 'get_document']
[3] Converted the tool definitions for the LLM

From here on, every question is sent to the LLM along with the tools.

Question: Can I bring my dog?
  -> sending the question and the tools to the LLM...
  -> tool call: search({'top_k': 5, 'query': 'can I bring a dog'})
  -> got the search results
  -> asking the LLM to answer from them...

[Answer]
Yes, you can bring your dog. The Wandering Kettle allows dogs on the small
terrace at the top of the stairs but not inside the room itself. There is a
water bowl by the terrace door, and assistance animals are welcome anywhere.

Question: What documents can you search?
  -> sending the question and the tools to the LLM...
  -> tool call: list_documents({})
  -> got the search results
  -> asking the LLM to answer from them...

[Answer]
The documents that can be searched are:

- allergens.txt
- faq.txt
- hours_access.txt
- menu_drinks.txt
- menu_food.txt
- staff_handbook.txt
- story.txt

Question: quit
Bye.
```

起動に10〜20秒、1問あたり数十秒から数分かかる。CPU で推論しているためで、
待ち時間のほとんどは LLM への2回の問い合わせである（10章）。

**2つの質問で、呼ばれたツールが違う。** 1問目は `search`、2問目は `list_documents` である。
クライアントは選んでいない。**渡した3つの中から LLM が選び、その名前を返してきた**だけである。

### 起動時の3行

質問を受け付ける前に、クライアントは3つのことを済ませている。

| 表示 | 中身 | どこで見たか |
|------|------|------------|
| `[1] Connected to the MCP server` | サーバーを起動し、`initialize` を送った | 6章・7章 |
| `[2] Tools reported by the server: [...]` | `tools/list` の結果。3つ返る | 6章・7章 |
| `[3] Converted the tool definitions for the LLM` | Ollama 形式への詰め替え | 9章 |

**ここまでに LLM は登場しない。** 接続とツールの確認は MCP だけで終わる。

### 質問するたびに起きること

表示される行が、そのまま処理の順番である。

| 表示 | 何をしているか |
|------|--------------|
| `-> sending the question and the tools to the LLM...` | 1回目の POST（判断） |
| `-> tool call: search({...})` | 返ってきた `tool_calls` |
| `-> got the search results` | `tools/call` の結果 |
| `-> asking the LLM to answer from them...` | 2回目の POST（作文） |

`quit` と入力すると終わる。`async with` を抜けるので、MCP サーバーも一緒に終了する。

### 続けて質問しても、前回は覚えていない

Ollama は前回の `messages` を覚えていない。続きを話したければ、
過去のやりとりを**全部** `messages` に並べて毎回送る。

MCP の方はセッションが続いていた（7章）。**同じ「接続」でも性質が違う。**

| | どこに状態があるか |
|---|---|
| MCP サーバー | 接続が開いている間、クライアントとの対応が続く |
| Ollama | どこにも無い。毎回1回きりの POST |

この教材のクライアントは、会話履歴を持たない。質問は1問ごとに独立している。
**MCP と検索の流れを追うのが目的で、会話管理はそこに関係しないからである。**

### JSON-RPC を覗く

`RAG_DEBUG=1` を付けると、MCP サーバーとやりとりしている JSON がそのまま出る。

```bash
docker compose exec app env RAG_DEBUG=1 uv run python -m client.main
```

```
[JSON-RPC] -> sent: tools/list
{
  "method": "tools/list"
}

[JSON-RPC] <- received: tools/list
{
  "tools": [
    {
      "name": "search",
      "description": "\nSearch the documents of a cafe called The Wandering Kettle.\n\nUse this to answer questions about the menu, prices, opening hours,\nlocation, wifi and power sockets, allergies and dietary options, the\ns...",
      "inputSchema": {
        "properties": {
          "query": {"title": "Query", "type": "string"},
          "top_k": {"default": 5, "title": "Top K", "type": "integer"}
        },
        "required": ["query"],
        "type": "object",
        "title": "searchArguments"
      }
    },
    { "name": "list_documents", ... },
    { "name": "get_document",   ... }
  ]
}

[2] Tools reported by the server: ['search', 'list_documents', 'get_document']
[3] Converted the tool definitions for the LLM

Question: Can I bring my dog?
  -> sending the question and the tools to the LLM...
  -> tool call: search({'top_k': 5, 'query': 'can I bring a dog'})

[JSON-RPC] -> sent: tools/call
{
  "method": "tools/call",
  "params": {
    "name": "search",
    "arguments": {"top_k": 5, "query": "can I bring a dog"}
  }
}

[JSON-RPC] <- received: tools/call
{
  "content": [
    {
      "type": "text",
      "text": "[1] source: faq.txt (distance: 0.21)\npassage: \nThe Wandering Kettle - Questions We Get Asked\n\nCAN I STAY AND WORK?\n\nYes, on most days. We ask for one order every ninety minutes, and we ask you\nto move..."
    }
  ]
}
```

6章で見たものと同じ形が流れている。
長い文字列は200文字で切って表示している（`debug_jsonrpc()`）。
この前に `initialize` のやりとりも表示されるが、ここでは省いた。
残り2つのツールの定義も同様である。

## この先

**ここまでで、MCP で動く RAG が1つ手元にある。** 広げ方を3つ挙げておく。

- **資料を差し替える。** `data/documents/` を自分のテキストに置き換えて再インデックスすれば、
  自分用の検索付き LLM になる（5章）
- **ツールを増やす。** `@mcp.tool()` を付けた関数をもう1つ書けば、それだけで増える（7章）。
  LLM がどれを選ぶかは、docstring の書き方で決まる
- **モデルを替える。** ツール呼び出しに対応していることだけ確かめる（8章・9章）
