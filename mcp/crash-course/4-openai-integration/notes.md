# 4-openai-integration — What’s in this folder

This folder shows how to **use an MCP server as the source of tools for an OpenAI model**. The LLM gets the MCP tools in OpenAI’s function-calling format, and when it decides to call a tool, the client runs that tool via MCP and sends the result back to OpenAI.

**Flow:** User query → OpenAI (with MCP tools) → LLM may request a tool call → client runs the tool on the MCP server → result goes back to OpenAI → final answer.

**Files:** `server.py` (MCP server with one tool), `client.py` (OpenAI + MCP client), `client-simple.py` (same idea, script-style), `data/kb.json` (knowledge base the server reads).

---

## server.py

**Role:** MCP server that exposes a **Knowledge Base** tool.

- **FastMCP** instance named `"Knowledge Base"`, configured for stdio (and optionally host/port for SSE; this example runs with `transport="stdio"`).
- **One tool:** `get_knowledge_base()`  
  - No parameters.  
  - Reads `data/kb.json` (list of Q&A objects: `question`, `answer`).  
  - Returns a single formatted string of all Q&As (or an error message if the file is missing/invalid).
- **Run:** `mcp.run(transport="stdio")` — so Cursor/Claude or any MCP client can talk to it over stdio.

So the server’s only job is to expose “get the full knowledge base text” as an MCP tool; it doesn’t call OpenAI.

---

## client.py

**Role:** Connects to the MCP server above, converts its tools to OpenAI’s format, and runs a **query loop** where OpenAI can call those tools; the client executes tool calls via MCP and feeds results back to OpenAI.

**Main pieces:**

1. **`MCPOpenAIClient`**
   - Holds: an OpenAI client (`AsyncOpenAI`), the MCP `ClientSession`, and the stdio transport.
   - `connect_to_server(server_script_path)`  
     - Starts the MCP server as a subprocess (e.g. `python server.py`).  
     - Connects via **stdio** (`StdioServerParameters` + `stdio_client`).  
     - Creates a `ClientSession`, calls `initialize()`, and optionally prints the list of tools.

2. **`get_mcp_tools()`**
   - Calls MCP `list_tools()`.
   - Converts each MCP tool to OpenAI’s function format: `type: "function"`, `function.name`, `function.description`, `function.parameters` (from the tool’s `inputSchema`).  
   - Returns that list for use in `chat.completions.create(..., tools=...)`.

3. **`process_query(query)`**
   - Gets tools with `get_mcp_tools()`.
   - Calls OpenAI with the user message and `tools` / `tool_choice="auto"`.
   - If the assistant message has **tool_calls**:
     - For each tool call: runs `session.call_tool(name, arguments)` on the MCP server.
     - Appends each tool result to the conversation as a `role: "tool"` message (with `tool_call_id` and `content`).
     - Calls OpenAI again with the full conversation and `tool_choice="none"` to get a final text reply.
   - If there are no tool calls, returns the assistant’s content as-is.
   - Returns the final string answer to the user.

**Example in `main()`:** Connect to `server.py`, then ask something like “What is our company’s vacation policy?” — OpenAI may call `get_knowledge_base`, the client runs it via MCP, and the model answers using the returned text.

**Summary:** `server.py` = MCP server that exposes the knowledge base as one tool. `client.py` = bridge: MCP tools → OpenAI format, and execute MCP tool calls when the LLM asks for them, so the model can use the knowledge base to answer the user.
