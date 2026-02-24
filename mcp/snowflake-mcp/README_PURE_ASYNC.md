# Pure Async MCP Server Guide

This guide explains how to build an MCP server using the **low-level async API** instead of FastMCP. This approach gives you full control over the server lifecycle, tool registration, and async execution.

---

## Table of Contents

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

Copy this skeleton to start your pure async MCP server:

```python
"""
Pure Async MCP Server - Minimal Skeleton
"""
import asyncio
from mcp.server import Server, NotificationOptions
from mcp.server import stdio as mcp_stdio
from mcp.server.models import InitializationOptions
import mcp.types as types


# ═══════════════════════════════════════════════════════════════════
# 1. CREATE THE SERVER INSTANCE
# ═══════════════════════════════════════════════════════════════════
server = Server("MyMCPServer")


# ═══════════════════════════════════════════════════════════════════
# 2. REGISTER TOOL LISTING HANDLER
# ═══════════════════════════════════════════════════════════════════
@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """Return list of available tools with their schemas."""
    return [
        types.Tool(
            name="my_tool",
            description="Description of what this tool does",
            inputSchema={
                "type": "object",
                "properties": {
                    "param1": {
                        "type": "string",
                        "description": "Description of param1",
                    }
                },
                "required": ["param1"],
            },
        )
    ]


# ═══════════════════════════════════════════════════════════════════
# 3. REGISTER TOOL CALL HANDLER
# ═══════════════════════════════════════════════════════════════════
@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Dispatch and execute tool calls."""
    if name == "my_tool":
        param1 = arguments.get("param1", "")
        # Your tool logic here
        result = f"You called my_tool with: {param1}"
        return [types.TextContent(type="text", text=result)]
    
    raise ValueError(f"Unknown tool: {name}")


# ═══════════════════════════════════════════════════════════════════
# 4. DEFINE ASYNC MAIN FUNCTION
# ═══════════════════════════════════════════════════════════════════
async def main() -> None:
    """Set up and run the MCP server."""
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


# ═══════════════════════════════════════════════════════════════════
# 5. START THE EVENT LOOP
# ═══════════════════════════════════════════════════════════════════
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
uv run server_pure_mcp_enhanced.py
```

### Option 2: With MCP Inspector (for testing)

```bash
uv run mcp dev server_pure_mcp_enhanced.py
```

Then open http://localhost:6274 in your browser.

### Option 3: With Claude Desktop / Cursor

Add to your MCP configuration:

```json
{
  "mcpServers": {
    "my-server": {
      "command": "uv",
      "args": ["run", "server_pure_mcp_enhanced.py"],
      "cwd": "/path/to/your/project"
    }
  }
}
```

---

## Comparison: Same Tool in Both Approaches

### FastMCP Version

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("MyMCPServer")

@mcp.tool()
def my_tool(param1: str) -> str:
    """Description of what this tool does."""
    return f"You called my_tool with: {param1}"

mcp.run(transport="stdio")
```

### Pure Async Version

```python
import asyncio
from mcp.server import Server, NotificationOptions
from mcp.server import stdio as mcp_stdio
from mcp.server.models import InitializationOptions
import mcp.types as types

server = Server("MyMCPServer")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="my_tool",
            description="Description of what this tool does",
            inputSchema={
                "type": "object",
                "properties": {
                    "param1": {"type": "string", "description": "The parameter"},
                },
                "required": ["param1"],
            },
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "my_tool":
        param1 = arguments.get("param1", "")
        result = f"You called my_tool with: {param1}"
        return [types.TextContent(type="text", text=result)]
    raise ValueError(f"Unknown tool: {name}")

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

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Full Example: `server_pure_mcp_enhanced.py` Explained

The `server_pure_mcp_enhanced.py` file is a complete pure async MCP server with sophisticated features matching production-grade implementations. Here's a breakdown of its architecture:

### File Structure

```
server_pure_mcp_enhanced.py
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

### Environment Variables

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

**Response:**

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

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         MCP Client (Cursor/Claude)                   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ JSON-RPC over stdio
┌─────────────────────────────────────────────────────────────────────┐
│                       server_pure_mcp_enhanced.py                    │
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

- `server.py` - FastMCP version (simple)
- `server_enhanced.py` - FastMCP with class structure
- `server_pure_mcp_enhanced.py` - Full pure async example with Snowflake
- `config.py` - Pydantic configuration models
- `EVOLUTION_GUIDE.md` - Learning path from basic to sophisticated
- `README.md` - FastMCP documentation
