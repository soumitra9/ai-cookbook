# client-stdio.py vs client-sse.py

Both are MCP **clients**: they connect to the same Calculator server, list tools, and call `add(2, 3)`. The only difference is **how** they connect — the transport.

---

## client-stdio.py (stdio transport)

- **Imports**: `StdioServerParameters`, `stdio_client`
- **Connection**: Spawns the server as a **subprocess** and talks over stdin/stdout.
- **Server params**: You pass the command to run the server:
  - `command="python"`, `args=["server.py"]`
  - The client starts `server.py` itself; no separate server process needed.
- **Server must use**: `mcp.run(transport="stdio")` (default in this example).
- **Use when**: Server and client run on the same machine; you want the client to own the server process (e.g. scripts, tests, same host).

**Run**: Start the client only (it starts the server for you):
  `uv run client-stdio.py`

---

## client-sse.py (SSE transport)

- **Imports**: `sse_client` (no StdioServerParameters)
- **Connection**: Connects to an **already running** server over HTTP (Server-Sent Events) at a URL.
- **URL**: `http://localhost:8050/sse` — the server must be listening on that port/path.
- **Server must use**: `mcp.run(transport="sse")` and be started **before** the client.
- **Use when**: Server runs as a separate process (or on another machine); you want HTTP-based, network-friendly access.

**Run**: Two steps:
  1. Start the server: `uv run server.py` (with `transport = "sse"` in server.py)
  2. In another terminal: `uv run client-sse.py`

---

## Summary

|                    | client-stdio.py        | client-sse.py              |
|--------------------|------------------------|----------------------------|
| Transport          | stdio (stdin/stdout)   | SSE over HTTP              |
| Who starts server  | Client spawns server   | You start server manually  |
| Server config      | `transport="stdio"`    | `transport="sse"`          |
| Network            | Same process / machine | Can be remote (URL)        |
| Typical use       | Scripts, tests, same host | Separate process, HTTP API |

Same MCP protocol and session usage (`list_tools`, `call_tool`); only the transport layer differs.
