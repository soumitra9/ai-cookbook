# Snowflake MCP Server (Pure Async)

A production-ready MCP server for Snowflake using the **low-level async API** instead of FastMCP. This approach gives you full control over the server lifecycle, tool registration, and async execution.

---

## 📄 Quick Reference: Template File

> **New to pure async MCP?** Start with the template:
> 
> ```
> server_template_pure_async.py   ← Minimal skeleton (copy this to start)
> server.py                       ← Full implementation with Snowflake
> ```
> 
> The template file shows the **5 must-have components** for any pure async MCP server in a clean, copy-paste ready format.

---

## Features

- **Persistent connection** with health checks
- **Query validation** (QueryValidator class)
- **Timeout control** (per-query override)
- **Query tagging** (auto-generated if not provided)
- **Cache control** (disable_cache parameter)
- **Row limiting** (max_query_rows config)
- **Full response metadata** (query_id, has_more_rows, etc.)

---

## Available Tools

| Tool | Description | Required Parameters | Optional Parameters |
|------|-------------|---------------------|---------------------|
| `execute_query` | Execute a read-only SQL query (SELECT, WITH, SHOW, DESCRIBE, EXPLAIN) | `query` | `timeout_seconds`, `query_tag`, `disable_cache` |
| `list_databases` | List all databases in Snowflake | - | - |
| `list_schemas` | List all schemas in a database | `database` | - |
| `list_tables` | List all tables in a database schema | `database`, `schema` | - |
| `describe_table` | Get detailed table structure (columns, types, nullability) | `database`, `schema`, `table` | - |
| `check_database_exists` | Validate that a database (and optionally schema) is accessible | `database` | `schema` |

---

## Configuration Models (`config.py`)

The server uses **Pydantic models** for type-safe, validated configuration. This provides:
- ✅ Type validation at startup
- ✅ Clear error messages for missing env vars
- ✅ Default values for optional fields
- ✅ Easy conversion to connection parameters

### SnowflakeConfig

Handles Snowflake connection settings:

```python
class SnowflakeConfig(BaseModel):
    account: str          # Required - Snowflake account identifier
    user: str             # Required - Snowflake username
    password: str         # Required - Snowflake password
    warehouse: str | None # Optional - Default warehouse
    database: str | None  # Optional - Default database
    schema_name: str | None # Optional - Default schema
    role: str | None      # Optional - Default role
    timeout: int = 30     # Default query timeout (seconds)
```

| Field | Env Variable | Required | Default | Description |
|-------|--------------|----------|---------|-------------|
| `account` | `SNOWFLAKE_ACCOUNT` | ✅ Yes | - | Account ID (e.g., `abc12345.us-east-1`) |
| `user` | `SNOWFLAKE_USER` | ✅ Yes | - | Username |
| `password` | `SNOWFLAKE_PASSWORD` | ✅ Yes | - | Password |
| `warehouse` | `SNOWFLAKE_WAREHOUSE` | No | `None` | Default warehouse |
| `database` | `SNOWFLAKE_DATABASE` | No | `None` | Default database |
| `schema_name` | `SNOWFLAKE_SCHEMA` | No | `None` | Default schema |
| `role` | `SNOWFLAKE_ROLE` | No | `None` | Default role |
| `timeout` | `SNOWFLAKE_TIMEOUT` | No | `30` | Query timeout (seconds) |

**Key Methods:**
- `from_env()` - Load config from environment variables
- `to_connection_params()` - Convert to `snowflake.connector.connect()` kwargs

### ServerConfig

Handles MCP server settings:

```python
class ServerConfig(BaseModel):
    log_level: str = "INFO"       # DEBUG, INFO, WARNING, ERROR
    max_query_rows: int = 10000   # Max rows returned per query
```

| Field | Env Variable | Default | Description |
|-------|--------------|---------|-------------|
| `log_level` | `LOG_LEVEL` | `INFO` | Logging verbosity |
| `max_query_rows` | `MAX_QUERY_ROWS` | `10000` | Row limit for queries |

### Usage in Server

```python
# In SnowflakeMCPServer class (lazy initialization)
@property
def snowflake_config(self) -> SnowflakeConfig:
    if self._snowflake_config is None:
        self._snowflake_config = SnowflakeConfig.from_env()
    return self._snowflake_config

# Connect using config
self.connection = snowflake.connector.connect(
    **self.snowflake_config.to_connection_params()
)
```

---

## Quick Start

### 1. Install dependencies

```bash
uv sync
```

### 2. Set up environment variables

Create a `.env` file:

```bash
# Required
SNOWFLAKE_ACCOUNT=your-account-id
SNOWFLAKE_USER=your-username
SNOWFLAKE_PASSWORD=your-password

# Optional
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=MY_DB
SNOWFLAKE_SCHEMA=PUBLIC
SNOWFLAKE_ROLE=ANALYST
SNOWFLAKE_TIMEOUT=30          # Default query timeout (seconds)
MAX_QUERY_ROWS=10000          # Max rows returned per query
LOG_LEVEL=INFO
```

### 3. Run the server

```bash
uv run server.py
```

Or with MCP Inspector for testing:

```bash
# Note: `mcp dev` only works with FastMCP servers.
# For pure async servers, use npx directly:
npx @anthropic/mcp-inspector uv run server.py
```

> ⚠️ **Important**: `mcp dev server.py` does NOT work with pure async servers!
> It only supports FastMCP. Use `npx @anthropic/mcp-inspector` instead.

---

## Table of Contents

- [Available Tools](#available-tools)
- [Why Pure Async?](#why-pure-async)
- [FastMCP vs Pure Async Comparison](#fastmcp-vs-pure-async-comparison)
- [The 5 Must-Have Components](#the-5-must-have-components)
- [Minimal Skeleton](#minimal-skeleton)
- [Required Imports](#required-imports)
- [Component Deep Dive](#component-deep-dive)
- [Tool Schema Reference](#tool-schema-reference)
- [Response Types](#response-types)
- [Handling Blocking I/O](#handling-blocking-io)
- [Visual Flow Diagram](#visual-flow-diagram)
- [Adding Multiple Tools](#adding-multiple-tools)
- [Running the Server](#running-the-server)
- [Connection Flow (Detailed Example)](#connection-flow-detailed-example)
- [What the LLM Actually Receives](#what-the-llm-actually-receives-response-format)

---

## Why Pure Async?

| Benefit | Explanation |
|---------|-------------|
| **Fine-grained control** | You decide exactly how tools are listed, called, and responses formatted |
| **Custom initialization** | Set server version, capabilities, experimental features |
| **Multiple tools routing** | Easy to add complex dispatch logic |
| **Better error handling** | Full control over exception handling and error messages |
| **Concurrency control** | Manage how blocking operations interact with async |
| **Advanced features** | Add resources, prompts, notifications more easily |

---

## FastMCP vs Pure Async Comparison

| Aspect | FastMCP | Pure Async |
|--------|---------|------------|
| **Complexity** | 3 lines to wire up | ~30 lines of boilerplate |
| **Control** | Library handles everything | You control the flow |
| **Functions** | Synchronous (`def`) | Asynchronous (`async def`) |
| **Event Loop** | Hidden inside FastMCP | You manage it explicitly |
| **Tool Registration** | Automatic from type hints | Manual schema definition |
| **Best For** | Prototyping, simple servers | Production, complex servers |

Think of it like:
- **FastMCP** = Automatic transmission (easy to drive)
- **Pure Async** = Manual transmission (full control)

---

## The 5 Must-Have Components

| # | Component | Code | Purpose |
|---|-----------|------|---------|
| 1 | **Server Instance** | `server = Server("Name")` | Creates MCP server object |
| 2 | **List Tools Handler** | `@server.list_tools()` | Tells clients what tools exist |
| 3 | **Call Tool Handler** | `@server.call_tool()` | Executes tool when client calls it |
| 4 | **Async Main** | `async def main()` | Sets up stdio streams & runs server |
| 5 | **Event Loop Start** | `asyncio.run(main())` | Starts the async event loop |

---

## Minimal Skeleton

**📄 See `server_template_pure_async.py` for a complete, copy-paste ready template.**

Or copy this minimal skeleton:

```python
import asyncio
from mcp.server import Server, NotificationOptions
from mcp.server import stdio as mcp_stdio
from mcp.server.models import InitializationOptions
import mcp.types as types

# 1. CREATE SERVER
server = Server("MyMCPServer")

# 2. LIST TOOLS
@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="my_tool",
            description="What this tool does",
            inputSchema={
                "type": "object",
                "properties": {
                    "param1": {"type": "string", "description": "..."},
                },
                "required": ["param1"],
            },
        )
    ]

# 3. CALL TOOL
@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "my_tool":
        return [types.TextContent(type="text", text=f"Result: {arguments}")]
    raise ValueError(f"Unknown tool: {name}")

# 4. ASYNC MAIN
async def main() -> None:
    options = InitializationOptions(
        server_name="MyMCPServer",
        server_version="0.1.0",
        capabilities=server.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )
    async with mcp_stdio.stdio_server() as (read, write):
        await server.run(read, write, options)

# 5. START EVENT LOOP
if __name__ == "__main__":
    asyncio.run(main())
```

---

## Required Imports

```python
import asyncio                              # For async event loop
from mcp.server import Server               # The MCP server class
from mcp.server import NotificationOptions  # For capabilities
from mcp.server import stdio as mcp_stdio   # For stdio transport
from mcp.server.models import InitializationOptions  # Server init config
import mcp.types as types                   # MCP type definitions (Tool, TextContent)
```

---

## Component Deep Dive

### 1. Server Instance

```python
server = Server("MyMCPServer")
```

Creates the MCP server object. The name is used for identification in logs and client connections.

### 2. List Tools Handler

```python
@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="my_tool",
            description="What this tool does",
            inputSchema={...},
        )
    ]
```

This function is called when a client sends `{"method": "tools/list"}`. It returns all available tools with their schemas so the client (LLM) knows what it can call.

### 3. Call Tool Handler

```python
@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "my_tool":
        # Execute tool logic
        return [types.TextContent(type="text", text="result")]
    
    raise ValueError(f"Unknown tool: {name}")
```

This function is called when a client sends `{"method": "tools/call", "params": {"name": "my_tool", "arguments": {...}}}`. You dispatch based on the tool name and return results.

### 4. Async Main Function

```python
async def main() -> None:
    options = InitializationOptions(
        server_name="MyMCPServer",
        server_version="0.1.0",
        capabilities=server.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )

    async with mcp_stdio.stdio_server() as (read, write):
        await server.run(read, write, options)
```

Sets up:
- **InitializationOptions**: Server metadata and capabilities
- **stdio_server()**: Async context manager for stdin/stdout streams
- **server.run()**: Starts the server loop listening for messages

### 5. Event Loop Start

```python
if __name__ == "__main__":
    asyncio.run(main())
```

Starts the Python asyncio event loop and runs your server.

---

## Tool Schema Reference

### Basic Tool Structure

```python
types.Tool(
    name="tool_name",           # String: unique identifier
    description="...",          # String: what it does (for LLM)
    inputSchema={               # JSON Schema object
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "..."},
            "param2": {"type": "number", "description": "..."},
            "param3": {"type": "boolean", "description": "..."},
        },
        "required": ["param1"],  # Which params are mandatory
    },
)
```

### JSON Schema Types

| Type | JSON Schema | Python Equivalent |
|------|-------------|-------------------|
| String | `{"type": "string"}` | `str` |
| Number | `{"type": "number"}` | `float` |
| Integer | `{"type": "integer"}` | `int` |
| Boolean | `{"type": "boolean"}` | `bool` |
| Array | `{"type": "array", "items": {...}}` | `list` |
| Object | `{"type": "object", "properties": {...}}` | `dict` |

### Example: Tool with Multiple Parameters

```python
types.Tool(
    name="search_database",
    description="Search the database with filters",
    inputSchema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query text",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum results to return",
                "default": 10,
            },
            "include_metadata": {
                "type": "boolean",
                "description": "Whether to include metadata in results",
                "default": False,
            },
        },
        "required": ["query"],
    },
)
```

---

## Response Types

### What is `types.TextContent`?

It's the **standard format** MCP uses to send data from your server back to the client (the LLM).

Think of it like a **shipping container** - you can't just throw your data at the LLM. You need to package it in a format MCP understands.

**Why is it needed?**

MCP is a **protocol** (like HTTP). Both sides need to agree on the message format:

```
┌─────────────────┐                      ┌─────────────────┐
│   Your Server   │  ──── MCP ────────►  │   LLM (Client)  │
│                 │                      │                 │
│  "Here's data"  │   Must be in         │  "I understand  │
│                 │   TextContent        │   TextContent"  │
└─────────────────┘   format!            └─────────────────┘
```

Without `TextContent`, the LLM wouldn't know how to interpret your response.

**Structure:**

```python
types.TextContent(type="text", text="Your actual message here")
```

| Field | Value | Meaning |
|-------|-------|---------|
| `type` | `"text"` | This is text content (not an image, not binary) |
| `text` | (your string) | The actual content the LLM sees |

**Why a list `[...]`?**

```python
return [types.TextContent(...)]
```

MCP allows returning **multiple content blocks** (like text + image). So it expects a list, even if you only have one item.

**Simple analogy:**

| Concept | Analogy |
|---------|---------|
| Your data | A letter you wrote |
| `TextContent` | The envelope |
| The list `[...]` | A mailbag (can hold multiple envelopes) |
| MCP protocol | The postal service rules |

---

### Text Response (Most Common)

```python
return [types.TextContent(type="text", text="Your result here")]
```

### JSON Response (As Text)

```python
import json
result = {"key": "value", "count": 42}
return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
```

### Multiple Content Blocks

```python
return [
    types.TextContent(type="text", text="## Summary"),
    types.TextContent(type="text", text="Detailed results here..."),
]
```

### Error Response

```python
# Raise an exception - MCP will convert to error response
raise ValueError("Invalid parameter: query cannot be empty")
```

---

### Output Format Design Choices

When building tools, you choose how to format the output. Here's the reasoning behind our schema exploration tools:

| Tool | Format | Why This Choice |
|------|--------|-----------------|
| `list_databases` | Bullet list | Single column of names. Bullets are clean and fast to scan. |
| `list_schemas` | Bullet list | Single column of names. Same reasoning as databases. |
| `list_tables` | Bullet list with extras | Primary info = name. Kind (TABLE/VIEW) and comment are secondary, so inline extras work. |
| `describe_table` | Tabular | 5 equally-important columns per row (name, type, nullable, default, comment). Needs alignment for comparison. |
| `check_database_exists` | Status + guidance | Validation result (✅/❌) + helpful next steps. Quick pass/fail with actionable info. |
| `execute_query` | Metadata + JSON | Metadata first for quick status check, JSON for structured data the LLM can parse. |

**When to use each format:**

**Bullet Lists** → Simple name lists
```
Available databases (3):
• ANALYTICS_DB
• STAGING_DB
• PROD_DB
```
✅ Clean, fast to scan
✅ Works well for 1-2 pieces of info per item
❌ Breaks down with many columns

**Tabular Format** → Multi-attribute data
```
Column                         Type                 Null?    Default         Comment
------------------------------------------------------------------------------------------
ID                             NUMBER(38,0)         NO                       Primary key
NAME                           VARCHAR(100)         YES                      
```
✅ Easy to compare values across rows
✅ Proper alignment for readability
❌ Overkill for simple lists

**Status + Guidance** → Validation tools
```
✅ Database 'ANALYTICS_DB' exists and is accessible.
   Found 5 schemas in this database.

💡 To query this database, use fully qualified names like:
   SELECT * FROM ANALYTICS_DB.schema_name.table_name
```
✅ Immediate pass/fail status
✅ Actionable guidance on next steps
✅ Helpful hints for the LLM

**Metadata + JSON** → Query results
```
Query executed successfully!
Rows returned: 100

Results:
[{"ID": 1, "NAME": "Alice"}, ...]
```
✅ Human-readable summary at top
✅ Structured data remains parseable
✅ LLM can extract specific values if needed

---

## Handling Blocking I/O

The Snowflake connector (and many database libraries) are **synchronous/blocking**. In an async server, you must run blocking code in a thread pool to avoid blocking the event loop.

### Pattern: run_in_executor

```python
@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "database_query":
        sql = arguments.get("sql", "")
        
        # Define blocking function
        def _blocking_database_call():
            # Synchronous database code here
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql)
                    return cur.fetchall()
        
        # Run in thread pool to not block event loop
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, _blocking_database_call)
        
        return [types.TextContent(type="text", text=str(result))]
```

### Why This Matters

```
WITHOUT run_in_executor:
  Event Loop: [blocked] [blocked] [blocked] [blocked]
  Other requests: WAITING...
  
WITH run_in_executor:
  Event Loop: [free] [free] [free] [free]
  Thread Pool: [doing database work]
  Other requests: Can be processed!
```

---

## Visual Flow Diagram

```
┌──────────────────────────────────────────────────────────────┐
│  if __name__ == "__main__":                                  │
│      asyncio.run(main())  ─────────────────────────┐         │
└──────────────────────────────────────────────────────────────┘
                                                     │
                                                     ▼
┌──────────────────────────────────────────────────────────────┐
│  async def main():                                           │
│      options = InitializationOptions(...)                    │
│      async with mcp_stdio.stdio_server() as (read, write):  │
│          await server.run(read, write, options)  ◄───────┐   │
└──────────────────────────────────────────────────────────│───┘
                                                           │
         ┌─────────────────────────────────────────────────┘
         │ Server listens for JSON-RPC messages
         ▼
┌──────────────────────────────────────────────────────────────┐
│  Client sends: {"method": "tools/list"}                      │
│                        │                                     │
│                        ▼                                     │
│  @server.list_tools()                                        │
│  async def handle_list_tools():                              │
│      return [types.Tool(name="my_tool", ...)]               │
└──────────────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────┐
│  Client sends: {"method": "tools/call", "params": {...}}     │
│                        │                                     │
│                        ▼                                     │
│  @server.call_tool()                                         │
│  async def handle_call_tool(name, arguments):                │
│      if name == "my_tool":                                   │
│          return [types.TextContent(type="text", text=...)]  │
└──────────────────────────────────────────────────────────────┘
```

---

## Adding Multiple Tools

### Step 1: Add to list_tools

```python
@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="run_query",
            description="Execute a read-only SQL query",
            inputSchema={
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "SQL query"},
                },
                "required": ["sql"],
            },
        ),
        types.Tool(
            name="list_tables",
            description="List all tables in a schema",
            inputSchema={
                "type": "object",
                "properties": {
                    "database": {"type": "string", "description": "Database name"},
                    "schema": {"type": "string", "description": "Schema name"},
                },
                "required": ["database", "schema"],
            },
        ),
        types.Tool(
            name="describe_table",
            description="Get table structure",
            inputSchema={
                "type": "object",
                "properties": {
                    "table": {"type": "string", "description": "Table name"},
                },
                "required": ["table"],
            },
        ),
    ]
```

### Step 2: Add dispatch logic in call_tool

```python
@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "run_query":
        sql = arguments.get("sql", "")
        result = await execute_query(sql)
        return [types.TextContent(type="text", text=json.dumps(result))]
    
    elif name == "list_tables":
        database = arguments.get("database", "")
        schema = arguments.get("schema", "")
        result = await list_tables(database, schema)
        return [types.TextContent(type="text", text=json.dumps(result))]
    
    elif name == "describe_table":
        table = arguments.get("table", "")
        result = await describe_table(table)
        return [types.TextContent(type="text", text=json.dumps(result))]
    
    raise ValueError(f"Unknown tool: {name}")
```

---

## Running the Server

### Option 1: Direct Execution

```bash
uv run server.py
```

### Option 2: With MCP Inspector (for testing)

```bash
# ⚠️ DO NOT use: mcp dev server.py (only works with FastMCP!)
# Use npx directly for pure async servers:
npx @anthropic/mcp-inspector uv run server.py
```

Then open http://localhost:6274 in your browser.

> **Why not `mcp dev`?**
> The `mcp dev` command specifically looks for FastMCP server objects.
> Pure async servers using the low-level `Server` class require `npx @anthropic/mcp-inspector`.

### Option 3: With Claude Desktop / Cursor

Add to your MCP configuration:

```json
{
  "mcpServers": {
    "snowflake-mcp-pure": {
      "command": "uv",
      "args": ["run", "server.py"],
      "cwd": "/path/to/snowflake-mcp-pure"
    }
  }
}
```

---

## Full Example: `server.py` Explained

The `server.py` file is a complete pure async MCP server with sophisticated features matching production-grade implementations. Here's a breakdown of its architecture:

### File Structure

```
server.py
├── Imports & Configuration
├── QueryValidator Class          # SQL validation
├── SnowflakeMCPServer Class      # Connection & query logic
├── MCP Server Wiring             # Tool registration
└── Entry Point                   # Async main
```

---

### 1. Configuration with Pydantic (`config.py`)

The server uses Pydantic models for type-safe configuration:

```python
# config.py
class SnowflakeConfig(BaseModel):
    account: str                    # Required
    user: str                       # Required
    password: str                   # Required
    warehouse: Optional[str]        # Optional
    database: Optional[str]         # Optional
    schema_name: Optional[str]      # Optional
    role: Optional[str]             # Optional
    timeout: int = 30               # Default query timeout

class ServerConfig(BaseModel):
    log_level: str = "INFO"
    max_query_rows: int = 10000     # Row limit for queries
```

**Why Pydantic?**
- Type validation at startup
- Clear error messages for missing env vars
- Default values
- Easy conversion to connection params

---

### 2. QueryValidator Class

Comprehensive SQL validation that goes beyond simple prefix checking:

```python
class QueryValidator:
    ALLOWED_STATEMENTS = {'SELECT', 'WITH', 'SHOW', 'DESCRIBE', 'DESC', 'EXPLAIN'}
    
    FORBIDDEN_KEYWORDS = {
        'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 'TRUNCATE',
        'REPLACE', 'MERGE', 'COPY', 'PUT', 'GET', 'REMOVE', 'GRANT', 'REVOKE',
        'USE ROLE', 'USE WAREHOUSE', 'USE DATABASE', 'USE SCHEMA'
    }
```

**Validation Steps:**
1. **Normalize query** - Remove comments (`-- ...`, `/* ... */`), normalize whitespace
2. **Check allowed statements** - Query must start with SELECT, WITH, SHOW, etc.
3. **Check forbidden keywords** - Scan entire query for dangerous operations
4. **Validate CTEs** - Ensure `WITH` queries end with `SELECT`

```python
@classmethod
def is_read_only_query(cls, query: str) -> tuple[bool, str]:
    """Returns (is_valid, error_message)"""
    normalized_query = cls._normalize_query(query)
    
    if not cls._starts_with_allowed_statement(normalized_query):
        return False, "Query must start with one of: ..."
    
    forbidden_found = cls._contains_forbidden_keywords(normalized_query)
    if forbidden_found:
        return False, f"Query contains forbidden operation: {forbidden_found}"
    
    return True, ""
```

---

### 3. SnowflakeMCPServer Class

The main server class with persistent connection and health checks:

#### Connection Management

```python
class SnowflakeMCPServer:
    def __init__(self):
        self.snowflake_config = SnowflakeConfig.from_env()
        self.server_config = ServerConfig.from_env()
        self.connection: Optional[SnowflakeConnection] = None  # Persistent
    
    async def connect(self) -> bool:
        """Establish connection with health checks."""
        # Check if existing connection is healthy
        if self.connection and not self.connection.is_closed():
            logger.info("✅ Reusing existing healthy connection")
            return True
        
        # Create new connection
        self.connection = snowflake.connector.connect(
            **self.snowflake_config.to_connection_params()
        )
        return True
```

**Connection Strategy:**
- **First call**: Creates new connection
- **Subsequent calls**: Reuses if healthy, reconnects if closed
- **Cleanup**: Disconnects on server shutdown

#### Connection Flow (Detailed Example)

Here's the complete flow when a query is executed:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           EXAMPLE: User sends query                              │
│                     "SELECT * FROM users LIMIT 10"                               │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  STEP 1: MCP Client calls tool                                                   │
│  ─────────────────────────────────────────────────────────────────────────────  │
│  Client sends JSON-RPC:                                                          │
│  {                                                                               │
│    "method": "tools/call",                                                       │
│    "params": {                                                                   │
│      "name": "execute_query",                                                    │
│      "arguments": {"query": "SELECT * FROM users LIMIT 10"}                     │
│    }                                                                             │
│  }                                                                               │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  STEP 2: handle_call_tool() receives request                                     │
│  ─────────────────────────────────────────────────────────────────────────────  │
│                                                                                  │
│  @server.call_tool()                                                             │
│  async def handle_call_tool(name: str, arguments: dict):                         │
│      if name == "execute_query":                                                 │
│          query = arguments.get("query")  # "SELECT * FROM users LIMIT 10"       │
│                                                                                  │
│          # Validate query is read-only                                           │
│          is_valid, error = QueryValidator.is_read_only_query(query)  ──► ✅      │
│                                                                                  │
│          # Call snowflake_server.execute_query()                                 │
│          result = await snowflake_server.execute_query(query=query, ...)        │
│                        │                                                         │
└────────────────────────│────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  STEP 3: execute_query() is called                                               │
│  ─────────────────────────────────────────────────────────────────────────────  │
│                                                                                  │
│  async def execute_query(self, query, timeout_seconds, query_tag, disable_cache):│
│                                                                                  │
│      # ⭐ FIRST: Ensure we have a connection                                     │
│      if not await self.connect():   ◄─── Goes to STEP 4                         │
│          raise Exception("Could not connect")                                    │
│                                                                                  │
│      # Generate query tag if not provided                                        │
│      query_tag = f"mcp_20260223_151030_123"  # auto-generated                   │
│                                                                                  │
│      # Execute the actual query                                                  │
│      result = await self._execute_query_with_options(query, ...)                │
│                        │                                                         │
└────────────────────────│────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  STEP 4: connect() - Connection Management                                       │
│  ─────────────────────────────────────────────────────────────────────────────  │
│                                                                                  │
│  async def connect(self) -> bool:                                                │
│                                                                                  │
│      # Check 1: Does connection exist?                                           │
│      if self.connection:                                                         │
│          │                                                                       │
│          │  # Check 2: Is it still healthy?                                      │
│          │  if not self.connection.is_closed():                                  │
│          │      logger.info("✅ Reusing existing healthy connection")            │
│          │      return True  ◄─── FAST PATH (no new connection needed)          │
│          │  else:                                                                │
│          │      logger.info("❌ Connection closed, need to reconnect")           │
│      else:                                                                       │
│          logger.info("❌ No existing connection, creating new one")              │
│                                                                                  │
│      # Create new connection (uses lazy-loaded config)                           │
│      self.connection = snowflake.connector.connect(                              │
│          **self.snowflake_config.to_connection_params()                          │
│      )        │                                                                  │
│               │                                                                  │
│               ▼                                                                  │
│      ┌─────────────────────────────────────────────────────────────────────┐    │
│      │  @property snowflake_config (LAZY LOAD)                             │    │
│      │  ─────────────────────────────────────────────────────────────────  │    │
│      │  if self._snowflake_config is None:                                 │    │
│      │      self._snowflake_config = SnowflakeConfig.from_env()            │    │
│      │      # ↑ Reads env vars: SNOWFLAKE_ACCOUNT, USER, PASSWORD          │    │
│      │  return self._snowflake_config                                      │    │
│      └─────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│      logger.info("✅ Successfully connected to Snowflake")                       │
│      return True                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  STEP 5: _execute_query_with_options() - Run in Thread Pool                      │
│  ─────────────────────────────────────────────────────────────────────────────  │
│                                                                                  │
│  def _run_query():  # ← Synchronous function (blocking)                          │
│      cursor = self.connection.cursor(DictCursor)                                 │
│                                                                                  │
│      # 1. Set session options                                                    │
│      cursor.execute("ALTER SESSION SET USE_CACHED_RESULT = FALSE")              │
│      cursor.execute("ALTER SESSION SET QUERY_TAG = 'mcp_20260223...'")          │
│                                                                                  │
│      # 2. Execute the actual query                                               │
│      cursor.execute("SELECT * FROM users LIMIT 10", timeout=30)                 │
│                                                                                  │
│      # 3. Fetch results                                                          │
│      query_id = cursor.sfqid  # e.g., "01abc-def-456..."                        │
│      columns = ["ID", "NAME", "EMAIL"]                                           │
│      rows = cursor.fetchmany(10000)  # max_query_rows limit                     │
│                                                                                  │
│      # 4. Reset session                                                          │
│      cursor.execute("ALTER SESSION SET QUERY_TAG = NULL")                        │
│      cursor.execute("ALTER SESSION SET USE_CACHED_RESULT = TRUE")               │
│                                                                                  │
│      cursor.close()  # Close cursor, but CONNECTION stays open!                  │
│                                                                                  │
│      return {"columns": [...], "rows": [...], "query_id": "..."}                │
│                                                                                  │
│  # ⭐ Run blocking code in thread pool (doesn't block async event loop)         │
│  loop = asyncio.get_running_loop()                                               │
│  return await loop.run_in_executor(None, _run_query)                             │
└─────────────────────────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  STEP 6: Return results to client                                                │
│  ─────────────────────────────────────────────────────────────────────────────  │
│                                                                                  │
│  Query executed successfully!                                                    │
│                                                                                  │
│  Query ID: 01abc-def-456-789                                                     │
│  Query tag: mcp_20260223_151030_123                                             │
│  Result cache: DISABLED                                                          │
│  Columns: ID, NAME, EMAIL                                                        │
│  Rows returned: 10                                                               │
│                                                                                  │
│  Results:                                                                        │
│  [{"ID": 1, "NAME": "Alice", "EMAIL": "alice@example.com"}, ...]                │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Key Connection Behaviors:**

| Scenario | What Happens |
|----------|--------------|
| **First Query (Cold Start)** | `connect()` → `self.connection is None` → Load config (lazy) → Create NEW connection (~100-500ms) → Store in `self.connection` → Execute query → Keep connection OPEN |
| **Subsequent Queries (Warm)** | `connect()` → `self.connection exists` → `is_closed()` returns `False` → ✅ REUSE existing connection (0ms) → Execute query immediately |
| **After Connection Dies** | `connect()` → `self.connection exists` → `is_closed()` returns `True` ❌ → Create NEW connection → Execute query |
| **Server Shutdown** | `main()` finally block runs → `snowflake_server.disconnect()` → Connection closed gracefully |

**The "Persistent Connection" Pattern:**

```python
# Connection is stored as instance variable
self.connection = None  # Initially

# First query: creates connection, stores it
self.connection = snowflake.connector.connect(...)

# Later queries: reuse same connection
cursor = self.connection.cursor()  # Uses stored connection
cursor.execute(sql)
cursor.close()  # Close cursor only, NOT connection

# Connection stays alive for next query!
```

This is why it's called **persistent** - the connection survives between queries.

#### Execute Query with Full Features

```python
async def execute_query(
    self,
    query: str,
    timeout_seconds: Optional[int] = None,    # Per-query timeout
    query_tag: Optional[str] = None,          # For tracking
    disable_cache: bool = True                # For accurate measurements
) -> Dict[str, Any]:
```

**Features:**
| Parameter | Purpose |
|-----------|---------|
| `timeout_seconds` | Override default timeout (1-3600 seconds) |
| `query_tag` | Identify queries in Snowflake history (auto-generated if not provided) |
| `disable_cache` | Disable result caching for accurate performance measurements |

**Session Management Flow:**

```python
def _run_query():
    cursor = self.connection.cursor(DictCursor)
    
    # 1. Set session options
    if disable_cache:
        cursor.execute("ALTER SESSION SET USE_CACHED_RESULT = FALSE")
    cursor.execute(f"ALTER SESSION SET QUERY_TAG = '{query_tag}'")
    
    # 2. Execute main query with timeout
    cursor.execute(query, timeout=timeout_seconds)
    
    # 3. Capture metadata
    query_id = cursor.sfqid
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchmany(max_query_rows)
    has_more = len(cursor.fetchmany(1)) > 0
    
    # 4. Reset session
    cursor.execute("ALTER SESSION SET QUERY_TAG = NULL")
    cursor.execute("ALTER SESSION SET USE_CACHED_RESULT = TRUE")
    
    return {
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
        "has_more_rows": has_more,
        "max_rows_returned": max_query_rows,
        "query_id": query_id,
        "query_tag": query_tag
    }
```

---

### 4. Tool Schema Definition

The `execute_query` tool schema matches the sophisticated server:

```python
@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="execute_query",
            description="Execute a read-only SQL query on Snowflake database...",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SQL query to execute (read-only operations only)"
                    },
                    "timeout_seconds": {
                        "type": "integer",
                        "description": "Optional timeout in seconds (1-3600)",
                        "minimum": 1,
                        "maximum": 3600
                    },
                    "query_tag": {
                        "type": "string",
                        "description": "Optional tag to identify this query..."
                    },
                    "disable_cache": {
                        "type": "boolean",
                        "description": "Disable Snowflake result caching (default: true)"
                    }
                },
                "required": ["query"]
            },
        )
    ]
```

---

### 5. Tool Call Handler

The dispatcher validates and executes queries:

```python
@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "execute_query":
        query = arguments.get("query")
        timeout_seconds = arguments.get("timeout_seconds")
        query_tag = arguments.get("query_tag")
        disable_cache = arguments.get("disable_cache", True)
        
        # Validate query
        is_valid, error_message = QueryValidator.is_read_only_query(query)
        if not is_valid:
            raise ValueError(f"Query validation failed: {error_message}")
        
        # Execute
        result = await snowflake_server.execute_query(
            query=query,
            timeout_seconds=timeout_seconds,
            query_tag=query_tag,
            disable_cache=disable_cache
        )
        
        # Format response
        output = f"Query executed successfully!\n"
        output += f"Query ID: {result['query_id']}\n"
        output += f"Query tag: {result['query_tag']}\n"
        # ... more formatting
        
        return [types.TextContent(type="text", text=output)]
```

---

### 6. Entry Point with Cleanup

```python
async def main() -> None:
    options = InitializationOptions(
        server_name="SnowflakeMCP",
        server_version="0.2.0",
        capabilities=server.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )

    try:
        async with mcp_stdio.stdio_server() as (read, write):
            await server.run(read, write, options)
    finally:
        # Clean up connection on exit
        await snowflake_server.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

**Key Points:**
- `try/finally` ensures connection cleanup
- Version bumped to `0.2.0` to reflect new features
- `disconnect()` closes Snowflake connection gracefully

---

### Example Usage

Call `execute_query` with full parameters:

```json
{
  "query": "SELECT * FROM my_database.my_schema.users LIMIT 100",
  "timeout_seconds": 120,
  "query_tag": "user_analysis_v1",
  "disable_cache": true
}
```

**Response (what the LLM receives):**

```
Query executed successfully!

Query ID: 01abc123-4567-89de-f012-34567890abcd
Query tag: user_analysis_v1
Result cache: DISABLED
Timeout: 120 seconds (2.0 minutes)
Columns: ID, NAME, EMAIL, CREATED_AT
Rows returned: 100

Results:
[
  {"ID": 1, "NAME": "Alice", "EMAIL": "alice@example.com", ...},
  {"ID": 2, "NAME": "Bob", "EMAIL": "bob@example.com", ...},
  ...
]
```

---

### What the LLM Actually Receives (Response Format)

When the MCP server returns results, the LLM receives a structured response via JSON-RPC. Here's the complete picture:

#### 1. MCP Protocol Response (JSON-RPC)

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Query executed successfully!\n\nQuery ID: 01abc123-4567-89de-f012-34567890abcd\nQuery tag: user_analysis_v1\n..."
      }
    ]
  }
}
```

#### 2. The TextContent Object

The server returns a list of `types.TextContent` objects:

```python
return [types.TextContent(type="text", text=output)]
```

| Field | Value | Description |
|-------|-------|-------------|
| `type` | `"text"` | Content type identifier |
| `text` | (formatted string) | The actual response the LLM sees |

#### 3. Formatted Text Structure

The `text` field contains a human-readable, structured response:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Query executed successfully!                        ← Status message        │
│                                                                              │
│ Query ID: 01abc123-4567-89de-f012-34567890abcd     ← For performance tracking│
│ Query tag: user_analysis_v1                         ← User-provided or auto  │
│ Result cache: DISABLED                              ← Cache status           │
│ Timeout: 120 seconds (2.0 minutes)                  ← Timeout used           │
│ Columns: ID, NAME, EMAIL, CREATED_AT                ← Column names           │
│ Rows returned: 100                                  ← Actual row count       │
│ ⚠️  Results limited to 10000 rows. Query returned   ← (Only if truncated)    │
│     more data.                                                               │
│                                                                              │
│ Results:                                                                     │
│ [                                                   ← JSON array of rows     │
│   {"ID": 1, "NAME": "Alice", ...},                                          │
│   {"ID": 2, "NAME": "Bob", ...},                                            │
│   ...                                                                        │
│ ]                                                                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 4. Response Fields Explained

| Field | Source | Purpose |
|-------|--------|---------|
| **Query ID** | `cursor.sfqid` | Snowflake's unique query identifier. Use this to find the query in Snowflake history or for performance analysis. |
| **Query tag** | User-provided or auto-generated | Tags queries for grouping and analysis. Auto-generated format: `mcp_YYYYMMDD_HHMMSS_mmm` |
| **Result cache** | `disable_cache` parameter | Shows whether Snowflake result caching was disabled. Default: DISABLED |
| **Timeout** | `timeout_seconds` or default | The timeout that was applied to this query |
| **Columns** | `cursor.description` | Column names from the result set |
| **Rows returned** | `len(rows)` | Actual number of rows in the response |
| **Results** | `cursor.fetchmany()` | JSON array of row dictionaries |

#### 5. Error Response Format

If an error occurs, the LLM receives:

```
Error executing execute_query: Query validation failed: Query must start with one of: DESC, DESCRIBE, EXPLAIN, SELECT, SHOW, WITH
```

Or for connection errors:

```
Error executing execute_query: Could not establish connection to Snowflake
```

#### 6. Code That Generates the Response

From `server.py`, the response formatting:

```python
@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    # ... validation and execution ...
    
    # Format results for display
    output = f"Query executed successfully!\n\n"
    
    if result.get('query_id'):
        output += f"Query ID: {result['query_id']}\n"
    
    output += f"Query tag: {result['query_tag']}\n"
    
    cache_status = "DISABLED" if disable_cache else "ENABLED"
    output += f"Result cache: {cache_status}\n"
    
    output += f"Timeout: {actual_timeout} seconds ({actual_timeout/60:.1f} minutes)\n"
    output += f"Columns: {', '.join(result['columns'])}\n"
    output += f"Rows returned: {result['row_count']}\n"
    
    if result['has_more_rows']:
        output += f"⚠️  Results limited to {result['max_rows_returned']} rows. Query returned more data.\n"
    
    output += "\nResults:\n"
    output += json.dumps(result['rows'], indent=2, default=str)
    
    return [types.TextContent(type="text", text=output)]
```

#### 7. Why This Format?

| Design Choice | Reason |
|---------------|--------|
| **Metadata first** | LLM can quickly see query status without parsing JSON |
| **Query ID prominent** | Essential for debugging and performance analysis |
| **Human-readable** | LLM can summarize results naturally to users |
| **JSON for data** | Structured data remains parseable if LLM needs to extract values |
| **Row limit warning** | Prevents LLM from assuming it has all data |

---

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         MCP Client (Cursor/Claude)                   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ JSON-RPC over stdio
┌─────────────────────────────────────────────────────────────────────┐
│                              server.py                               │
├─────────────────────────────────────────────────────────────────────┤
│  @server.list_tools()  ──► Returns execute_query schema              │
│  @server.call_tool()   ──► Validates & dispatches                    │
├─────────────────────────────────────────────────────────────────────┤
│                        QueryValidator                                │
│  ├─ _normalize_query()      (strip comments, whitespace)            │
│  ├─ _starts_with_allowed()  (SELECT, WITH, SHOW, etc.)             │
│  ├─ _contains_forbidden()   (INSERT, DELETE, DROP, etc.)           │
│  └─ _validate_cte_query()   (CTE ends with SELECT)                 │
├─────────────────────────────────────────────────────────────────────┤
│                     SnowflakeMCPServer                               │
│  ├─ connect()               (persistent with health checks)         │
│  ├─ disconnect()            (cleanup)                                │
│  └─ execute_query()         (timeout, tag, cache control)           │
│      └─ _execute_query_with_options()                               │
│          └─ run_in_executor() ──► Thread Pool ──► Snowflake         │
├─────────────────────────────────────────────────────────────────────┤
│                          config.py                                   │
│  ├─ SnowflakeConfig         (connection settings)                   │
│  └─ ServerConfig            (server settings)                        │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Snowflake Database                           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## See Also

| File | Description |
|------|-------------|
| `server_template_pure_async.py` | **Start here** - Minimal template with the 5 must-have components |
| `server.py` | Full Snowflake implementation |
| `config.py` | Pydantic configuration models |
| `EVOLUTION_GUIDE.md` | Learning path from basic to sophisticated |
| `CONNECTION_MANAGEMENT_GUIDE.md` | Deep dive into connection patterns |
