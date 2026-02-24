"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    PURE ASYNC MCP SERVER - TEMPLATE                          ║
║══════════════════════════════════════════════════════════════════════════════║
║                                                                              ║
║  This is a minimal template for building MCP servers using the low-level    ║
║  async API (not FastMCP). Copy this file as a starting point.               ║
║                                                                              ║
║  THE 5 MUST-HAVE COMPONENTS:                                                 ║
║  ┌─────┬─────────────────────────┬─────────────────────────────────────────┐ ║
║  │  #  │ Component               │ Purpose                                 │ ║
║  ├─────┼─────────────────────────┼─────────────────────────────────────────┤ ║
║  │  1  │ Server Instance         │ Creates MCP server object               │ ║
║  │  2  │ @server.list_tools()    │ Tells clients what tools exist          │ ║
║  │  3  │ @server.call_tool()     │ Executes tool when client calls it      │ ║
║  │  4  │ async def main()        │ Sets up stdio streams & runs server     │ ║
║  │  5  │ asyncio.run(main())     │ Starts the async event loop             │ ║
║  └─────┴─────────────────────────┴─────────────────────────────────────────┘ ║
║                                                                              ║
║  FLOW:                                                                       ║
║    asyncio.run(main()) → stdio_server() → server.run() → listen for calls   ║
║         ↓                                                                    ║
║    Client sends "tools/list" → handle_list_tools() → returns Tool schemas   ║
║         ↓                                                                    ║
║    Client sends "tools/call" → handle_call_tool() → executes & returns      ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
from mcp.server import Server, NotificationOptions
from mcp.server import stdio as mcp_stdio
from mcp.server.models import InitializationOptions
import mcp.types as types


# ═══════════════════════════════════════════════════════════════════════════════
# COMPONENT 1: CREATE THE SERVER INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════
# The server name appears in logs and client connections.

server = Server("MyMCPServer")


# ═══════════════════════════════════════════════════════════════════════════════
# COMPONENT 2: REGISTER TOOL LISTING HANDLER
# ═══════════════════════════════════════════════════════════════════════════════
# Called when client sends: {"method": "tools/list"}
# Returns all available tools with their JSON schemas.

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """Return list of available tools with their schemas."""
    return [
        types.Tool(
            name="my_tool",
            description="Description of what this tool does (shown to LLM)",
            inputSchema={
                "type": "object",
                "properties": {
                    "param1": {
                        "type": "string",
                        "description": "Description of param1",
                    },
                    # Add more parameters as needed:
                    # "param2": {"type": "integer", "description": "..."},
                    # "param3": {"type": "boolean", "description": "..."},
                },
                "required": ["param1"],  # List required parameters
            },
        ),
        # Add more tools here:
        # types.Tool(name="another_tool", description="...", inputSchema={...}),
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# COMPONENT 3: REGISTER TOOL CALL HANDLER
# ═══════════════════════════════════════════════════════════════════════════════
# Called when client sends: {"method": "tools/call", "params": {"name": "...", "arguments": {...}}}
# Dispatches to the correct tool and returns results.

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Dispatch and execute tool calls."""
    
    if name == "my_tool":
        # Extract arguments
        param1 = arguments.get("param1", "")
        
        # ─── YOUR TOOL LOGIC HERE ───
        result = f"You called my_tool with: {param1}"
        # ────────────────────────────
        
        return [types.TextContent(type="text", text=result)]
    
    # Add more tool handlers:
    # elif name == "another_tool":
    #     ...
    #     return [types.TextContent(type="text", text=result)]
    
    # Unknown tool
    raise ValueError(f"Unknown tool: {name}")


# ═══════════════════════════════════════════════════════════════════════════════
# COMPONENT 4: DEFINE ASYNC MAIN FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════
# Sets up server options and starts the stdio transport.

async def main() -> None:
    """Set up and run the MCP server."""
    
    # Server initialization options
    options = InitializationOptions(
        server_name="MyMCPServer",
        server_version="0.1.0",
        capabilities=server.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )

    # Start the server with stdio transport
    async with mcp_stdio.stdio_server() as (read, write):
        await server.run(read, write, options)


# ═══════════════════════════════════════════════════════════════════════════════
# COMPONENT 5: START THE EVENT LOOP
# ═══════════════════════════════════════════════════════════════════════════════
# Entry point - starts the asyncio event loop.

if __name__ == "__main__":
    asyncio.run(main())


# ═══════════════════════════════════════════════════════════════════════════════
# OPTIONAL: HANDLING BLOCKING I/O (e.g., database calls)
# ═══════════════════════════════════════════════════════════════════════════════
# If your tool calls synchronous/blocking code (like database connectors),
# wrap it in run_in_executor to avoid blocking the event loop:
#
#     async def my_async_tool():
#         def _blocking_call():
#             # Synchronous code here (e.g., database query)
#             return result
#
#         loop = asyncio.get_running_loop()
#         result = await loop.run_in_executor(None, _blocking_call)
#         return result
#
# ═══════════════════════════════════════════════════════════════════════════════
