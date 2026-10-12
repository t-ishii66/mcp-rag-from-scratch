"""
Step 2: Speaking MCP as raw JSON-RPC

This is the step the project exists for. No SDK is involved anywhere; the
server is driven directly.

    uv run python steps/02_mcp_raw.py

MCP over stdio turns out to be almost disappointingly plain.

    - start the server as a child process
    - write one line of JSON to its standard input
    - read one line of JSON from its standard output

That is the whole transport. No length header, no framing, no handshake format
of its own. A newline ends a message, and the message is ordinary JSON-RPC 2.0.

Every line sent and received is printed exactly as it went over the wire.
Tidying them up first would hide the thing this step exists to show.
"""

import json
import subprocess
import sys

# The protocol version to announce. A server that speaks it answers with the
# same string.
PROTOCOL_VERSION = "2025-06-18"

# How much of a long line to print. Truncation is always stated when it happens.
MAX_RAW_CHARS = 420


# =============================================================================
# Sending and receiving. This is all of it.
# =============================================================================

def send(proc: subprocess.Popen, message: dict) -> None:
    """Write the message to the server as one line of JSON."""
    line = json.dumps(message, ensure_ascii=False)

    print("\n-- sent ---------------------------------------------")
    print(show(line))

    proc.stdin.write(line + "\n")   # the newline is what ends the message
    proc.stdin.flush()              # without this the server waits forever


def receive(proc: subprocess.Popen) -> dict:
    """Read one line from the server and parse it as JSON."""
    line = proc.stdout.readline()
    if not line:
        raise RuntimeError("the server exited without answering")

    print("\n-- received -----------------------------------------")
    print(show(line.rstrip("\n")))

    return json.loads(line)


def show(line: str) -> str:
    """Prepare a raw line for printing, saying so if it had to be cut."""
    if len(line) <= MAX_RAW_CHARS:
        return line
    return f"{line[:MAX_RAW_CHARS]}\n   ... (cut here; the line is {len(line)} characters long)"


def explain(text: str) -> None:
    """A note from this script, kept visually apart from the traffic."""
    print(f"\n   {text}")


# =============================================================================
# Main
# =============================================================================

def main() -> None:
    print("=" * 72)
    print("Step 2: Speaking MCP as raw JSON-RPC")
    print("=" * 72)

    # -------------------------------------------------------------------------
    # [1] Start the server as a child process
    #
    # The server's stdout is the wire and must stay clean, which is why the
    # server logs to stderr. Here stderr is discarded to keep the output
    # readable.
    # -------------------------------------------------------------------------
    print("\n[1] Start the MCP server as a child process")
    explain("command: uv run python -m server.main")
    explain("it loads the embedding model first, so this takes a moment")

    proc = subprocess.Popen(
        ["uv", "run", "python", "-m", "server.main"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,   # the server's log, separate from the wire
        text=True,
        encoding="utf-8",
    )

    try:
        # ---------------------------------------------------------------------
        # [2] initialize - open the connection
        #
        # The first exchange, where both sides state their version and what
        # they can do. A message carrying an id is a request, and the answer
        # comes back carrying that same id.
        # ---------------------------------------------------------------------
        print("\n" + "=" * 72)
        print("[2] initialize - open the connection")
        print("=" * 72)

        send(proc, {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "raw-client", "version": "0.1.0"},
            },
        })
        result = receive(proc)

        server_name = result["result"]["serverInfo"]["name"]
        agreed = result["result"]["protocolVersion"]
        explain(f"the request had id=1 and the answer came back with id={result['id']}")
        explain(f"the server calls itself {server_name}, and agreed on {agreed}")

        # ---------------------------------------------------------------------
        # [3] notifications/initialized - send a notification
        #
        # This is a notification, not a request. The difference is that it
        # carries no id. Nothing comes back, so nothing should be read here:
        # reading would block until some later answer arrives.
        # ---------------------------------------------------------------------
        print("\n" + "=" * 72)
        print("[3] notifications/initialized - say we are ready")
        print("=" * 72)

        send(proc, {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        })

        explain("no id. that is what makes it a notification")
        explain("nothing is sent back, so nothing is read here")

        # ---------------------------------------------------------------------
        # [4] tools/list - ask what tools exist
        #
        # This is where the definitions that get handed to an LLM come from.
        # ---------------------------------------------------------------------
        print("\n" + "=" * 72)
        print("[4] tools/list - ask for the available tools")
        print("=" * 72)

        send(proc, {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
        })
        result = receive(proc)

        tools = result["result"]["tools"]
        explain(f"{len(tools)} tool(s) came back")
        for tool in tools:
            print(f"\n   name     : {tool['name']}")
            print(f"   arguments: {list(tool['inputSchema']['properties'])}")
            print(f"   required : {tool['inputSchema'].get('required', [])}")
            first_line = (tool.get("description") or "").strip().split("\n")[0]
            print(f"   summary  : {first_line}")

        explain("note the key: inputSchema, in camel case.")
        explain("the Python SDK calls it input_schema, but the wire says this.")

        # ---------------------------------------------------------------------
        # [5] tools/call - run the tool
        #
        # The retrieval from step 1 runs here, called across a process
        # boundary this time.
        # ---------------------------------------------------------------------
        print("\n" + "=" * 72)
        print("[5] tools/call - run the tool")
        print("=" * 72)

        send(proc, {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "search",
                "arguments": {"query": "can I bring a dog", "top_k": 1},
            },
        })
        result = receive(proc)

        # The result arrives in a content array, tagged by type.
        contents = result["result"]["content"]
        text = contents[0]["text"]
        explain(f"content has {len(contents)} item(s), of type {contents[0]['type']}")
        explain(f"the text is {len(text)} characters. its first lines:")
        for line in text.split("\n")[:4]:
            print(f"   |{line}")
        print("   |...")

    finally:
        # ---------------------------------------------------------------------
        # [6] Shut down
        #
        # Closing stdin gives the server an EOF, and it exits on its own.
        # ---------------------------------------------------------------------
        print("\n" + "=" * 72)
        print("[6] Shut down")
        print("=" * 72)
        explain("closing stdin -> the server sees EOF and stops")
        proc.stdin.close()
        proc.wait(timeout=15)
        explain(f"the server exited with code {proc.returncode}")

    print("\n" + "=" * 72)
    print("Talking MCP came down to writing and reading one line of JSON.")
    print("Step 3 writes these same four exchanges using the official SDK.")
    print("=" * 72)


if __name__ == "__main__":
    main()
