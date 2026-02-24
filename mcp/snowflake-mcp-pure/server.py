"""
Snowflake MCP Server (Pure Async)
==================================

A production-ready pure async MCP server for Snowflake.

┌─────────────────────────────────────────────────────────────────────────────┐
│  📄 For a minimal template, see: server_template_pure_async.py              │
│     That file shows the 5 must-have components for any pure async server.   │
└─────────────────────────────────────────────────────────────────────────────┘

This server extends the template with:
- Persistent connection with health checks
- Query validation (QueryValidator class)
- Timeout control (per-query override)
- Query tagging (auto-generated if not provided)
- Cache control (disable_cache parameter)
- Row limiting (max_query_rows config)
- Full response metadata (query_id, has_more_rows, etc.)

Authentication: Password-based (SNOWFLAKE_USER + SNOWFLAKE_PASSWORD)
"""

import os
import re
import json
import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import snowflake.connector
from snowflake.connector import DictCursor
from dotenv import load_dotenv

from mcp.server import Server, NotificationOptions
from mcp.server import stdio as mcp_stdio
from mcp.server.models import InitializationOptions
import mcp.types as types

from config import SnowflakeConfig, ServerConfig


# ---------------------------------------------------------------------------
# Configuration & Logging
# ---------------------------------------------------------------------------

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("snowflake-mcp")


# ---------------------------------------------------------------------------
# QueryValidator Class (from sophisticated server)
# ---------------------------------------------------------------------------

class QueryValidator:
    """Validates SQL queries to ensure they are read-only and safe."""
    
    # Allowed statement types for read-only operations
    ALLOWED_STATEMENTS = {
        'SELECT', 'WITH', 'SHOW', 'DESCRIBE', 'DESC', 'EXPLAIN'
    }
    
    # Dangerous keywords that indicate write operations
    FORBIDDEN_KEYWORDS = {
        'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 'TRUNCATE',
        'REPLACE', 'MERGE', 'COPY', 'PUT', 'GET', 'REMOVE', 'GRANT', 'REVOKE',
        'USE ROLE', 'USE WAREHOUSE', 'USE DATABASE', 'USE SCHEMA'
    }
    
    @classmethod
    def is_read_only_query(cls, query: str) -> tuple[bool, str]:
        """
        Validate if a query is read-only and safe to execute.
        
        Returns:
            tuple: (is_valid, error_message)
        """
        if not query or not query.strip():
            return False, "Query cannot be empty"
        
        # Clean and normalize the query
        normalized_query = cls._normalize_query(query)
        
        # Check if query starts with allowed statement
        if not cls._starts_with_allowed_statement(normalized_query):
            allowed = ', '.join(sorted(cls.ALLOWED_STATEMENTS))
            return False, f"Query must start with one of: {allowed}"
        
        # Check for forbidden keywords
        forbidden_found = cls._contains_forbidden_keywords(normalized_query)
        if forbidden_found:
            return False, f"Query contains forbidden operation: {forbidden_found}"
        
        # Additional checks for CTEs and complex queries
        if normalized_query.startswith('WITH'):
            if not cls._validate_cte_query(normalized_query):
                return False, "CTE query must end with a SELECT statement"
        
        return True, ""
    
    @classmethod
    def _normalize_query(cls, query: str) -> str:
        """Normalize query for analysis."""
        # Remove comments
        query = re.sub(r'--.*?\n', ' ', query)
        query = re.sub(r'/\*.*?\*/', ' ', query, flags=re.DOTALL)
        
        # Normalize whitespace
        query = re.sub(r'\s+', ' ', query.strip().upper())
        
        return query
    
    @classmethod
    def _starts_with_allowed_statement(cls, query: str) -> bool:
        """Check if query starts with an allowed statement."""
        for statement in cls.ALLOWED_STATEMENTS:
            if query.startswith(statement + ' ') or query == statement:
                return True
        return False
    
    @classmethod
    def _contains_forbidden_keywords(cls, query: str) -> Optional[str]:
        """Check for forbidden keywords in the query."""
        for keyword in cls.FORBIDDEN_KEYWORDS:
            # Use word boundaries to avoid false positives
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, query):
                return keyword
        return None
    
    @classmethod
    def _validate_cte_query(cls, query: str) -> bool:
        """Validate that CTE query ends with SELECT."""
        # Simple check: ensure there's a SELECT after the CTE definitions
        return 'SELECT' in query and query.rindex('SELECT') > query.index('WITH')


# ---------------------------------------------------------------------------
# SnowflakeMCPServer Class (with sophisticated features)
# ---------------------------------------------------------------------------

class SnowflakeMCPServer:
    """
    Main MCP server class for Snowflake integration.
    
    Features:
    - Persistent connection with health checks
    - Query validation
    - Timeout control
    - Query tagging
    - Cache control
    - Row limiting
    
    Note: Uses lazy initialization - config is loaded on first connect(),
    not at import time. This allows MCP Inspector to start without credentials.
    """
    
    def __init__(self) -> None:
        # Lazy initialization - config loaded on first connect()
        self._snowflake_config: Optional[SnowflakeConfig] = None
        self._server_config: Optional[ServerConfig] = None
        self.connection: Optional[snowflake.connector.SnowflakeConnection] = None
    
    # -------------------------------------------------------------------------
    # WHY LAZY INITIALIZATION?
    # -------------------------------------------------------------------------
    # We use @property with lazy loading instead of loading config in __init__.
    #
    # Problem with eager loading (in __init__):
    #   - SnowflakeConfig.from_env() raises RuntimeError if env vars are missing
    #   - This happens at MODULE IMPORT TIME (when snowflake_server = SnowflakeMCPServer())
    #   - MCP Inspector can't even start without credentials set
    #
    # Solution with lazy loading (@property):
    #   - Config is only loaded when first accessed (when a tool is called)
    #   - MCP Inspector can start and show available tools
    #   - Error only occurs when you actually try to execute a query
    #
    # This matches how FastMCP's server.py works - it only checks env vars
    # when the tool is actually called, not at import time.
    # -------------------------------------------------------------------------
    
    @property
    def snowflake_config(self) -> SnowflakeConfig:
        """Lazy-load Snowflake config on first access."""
        if self._snowflake_config is None:
            self._snowflake_config = SnowflakeConfig.from_env()
        return self._snowflake_config
    
    @property
    def server_config(self) -> ServerConfig:
        """Lazy-load server config on first access."""
        if self._server_config is None:
            self._server_config = ServerConfig.from_env()
            logger.setLevel(self._server_config.log_level)
        return self._server_config
    
    # ----- Connection Management -----------------------------------------------
    
    async def connect(self) -> bool:
        """Establish connection to Snowflake with health checks."""
        try:
            logger.info(f"🔍 Connection check - self.connection exists: {self.connection is not None}")
            
            if self.connection:
                is_closed = self.connection.is_closed()
                logger.info(f"🔍 Connection state - is_closed(): {is_closed}")
                if not is_closed:
                    logger.info("✅ Reusing existing healthy connection")
                    return True
                else:
                    logger.info("❌ Connection exists but is closed, need to reconnect")
            else:
                logger.info("❌ No existing connection, creating new one")
            
            logger.info("🔗 Connecting to Snowflake...")
            self.connection = snowflake.connector.connect(
                **self.snowflake_config.to_connection_params()
            )
            logger.info("✅ Successfully connected to Snowflake")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Snowflake: {e}")
            self.connection = None
            return False
    
    async def disconnect(self):
        """Close Snowflake connection."""
        if self.connection and not self.connection.is_closed():
            try:
                self.connection.close()
                logger.info("Disconnected from Snowflake")
            except Exception as e:
                logger.error(f"Error closing connection: {e}")
        self.connection = None
    
    # ----- Query Execution -----------------------------------------------------
    
    async def execute_query(
        self,
        query: str,
        timeout_seconds: Optional[int] = None,
        query_tag: Optional[str] = None,
        disable_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Execute a SQL query with full features from sophisticated server.
        
        Args:
            query: SQL query to execute
            timeout_seconds: Optional timeout override (1-3600 seconds)
            query_tag: Optional tag for query identification (auto-generated if not provided)
            disable_cache: Whether to disable Snowflake result caching (default: True)
        
        Returns:
            Dict with columns, rows, row_count, query_id, has_more_rows, max_rows_returned
        """
        if not await self.connect():
            raise Exception("Could not establish connection to Snowflake")
        
        # Use provided timeout or fall back to default
        query_timeout = timeout_seconds if timeout_seconds is not None else self.snowflake_config.timeout
        
        # Auto-generate query tag if not provided
        if not query_tag:
            query_tag = f"mcp_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]}"
        
        try:
            result = await self._execute_query_with_options(
                query, query_timeout, query_tag, disable_cache
            )
            return result
            
        except Exception as e:
            # Check for Snowflake timeout error (error code 604)
            if hasattr(e, 'errno') and e.errno == 604:
                error_msg = f"Query timed out after {query_timeout} seconds"
                logger.error(error_msg)
                raise Exception(error_msg)
            else:
                logger.error(f"Query execution failed: {e}")
                raise Exception(f"Query failed: {str(e)}")
    
    async def _execute_query_with_options(
        self,
        query: str,
        timeout_seconds: int,
        query_tag: str,
        disable_cache: bool
    ) -> Dict[str, Any]:
        """Execute query with session options (tag, cache control, timeout)."""
        
        def _run_query():
            cursor = self.connection.cursor(DictCursor)
            try:
                # Set cache control if disabled
                if disable_cache:
                    cursor.execute("ALTER SESSION SET USE_CACHED_RESULT = FALSE")
                
                # Set query tag
                escaped_tag = query_tag.replace("'", "''")
                cursor.execute(f"ALTER SESSION SET QUERY_TAG = '{escaped_tag}'")
                
                # Execute main query with timeout
                cursor.execute(query, timeout=timeout_seconds)
                
                # Capture query ID immediately after execution
                query_id = getattr(cursor, 'sfqid', None)
                
                # Get column information
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                
                # Fetch results with row limit
                rows = cursor.fetchmany(self.server_config.max_query_rows)
                
                # Check if there are more rows
                has_more = len(cursor.fetchmany(1)) > 0
                
                # Reset session settings
                cursor.execute("ALTER SESSION SET QUERY_TAG = NULL")
                if disable_cache:
                    cursor.execute("ALTER SESSION SET USE_CACHED_RESULT = TRUE")
                
                return {
                    "columns": columns,
                    "rows": rows,
                    "row_count": len(rows),
                    "has_more_rows": has_more,
                    "max_rows_returned": self.server_config.max_query_rows,
                    "query_id": query_id,
                    "query_tag": query_tag
                }
            finally:
                cursor.close()
        
        # Run the synchronous query in a thread pool to avoid blocking the event loop
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _run_query)


# ---------------------------------------------------------------------------
# MCP server wiring (low-level async API)
# ---------------------------------------------------------------------------

snowflake_server = SnowflakeMCPServer()
server = Server("SnowflakeMCP")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    
    Exposes execute_query with all parameters matching sophisticated server.
    """
    return [
        types.Tool(
            name="execute_query",
            description=(
                "Execute a read-only SQL query on Snowflake database. "
                "Supports SELECT, WITH (CTEs), SHOW, DESCRIBE, EXPLAIN commands."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SQL query to execute (read-only operations only)"
                    },
                    "timeout_seconds": {
                        "type": "integer",
                        "description": "Optional timeout in seconds for this query (overrides default timeout). Use for long-running queries or to set shorter timeouts.",
                        "minimum": 1,
                        "maximum": 3600
                    },
                    "query_tag": {
                        "type": "string",
                        "description": "Optional tag to identify this query for later analysis. Use descriptive tags like 'before_optimization', 'dashboard_query_1', or JSON strings like '{\"type\":\"test\",\"phase\":\"before\"}'. Makes it easy to find queries later for performance comparison."
                    },
                    "disable_cache": {
                        "type": "boolean",
                        "description": "Whether to disable Snowflake result caching for this query (default: true). Set to false only if you want to allow cached results. Disabling cache ensures accurate performance measurements for comparisons."
                    }
                },
                "required": ["query"]
            },
        ),

        types.Tool(
            name="list_databases",
            description="List all databases in Snowflake",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),

        types.Tool(
            name = "list_schemas",
            description="List all schemas in a database",
            inputSchema={
                "type": "object",
                "properties": {
                    "database": {"type": "string", "description": "Database name"},
                },
                "required": ["database"]
            }
        ),

        types.Tool(
            name="list_tables",
            description="List all tables in a database schema",
            inputSchema={
                "type": "object",
                "properties": {
                    "database": {
                        "type": "string",
                        "description": "Database name"
                    },
                    "schema": {
                        "type": "string",
                        "description": "Schema name"
                    }
                },
                "required": ["database", "schema"]
            },
        ),

        types.Tool(
            name="describe_table",
            description="Describe a table in a database schema",
            inputSchema={
                "type": "object",
                "properties": {
                    "database": {
                        "type": "string",
                        "description": "Database name"
                    },
                    "schema": {
                        "type": "string",
                        "description": "Schema name"
                    },
                    "table": {
                        "type": "string",
                        "description": "Table name"
                    }
                },
                "required": ["database", "schema", "table"]
            },
        ),

        types.Tool(
            name="check_database_exists",
            description="Validate that a database exists and is accessible. Optionally check a specific schema within the database.",
            inputSchema={
                "type": "object",
                "properties": {
                    "database": {
                        "type": "string",
                        "description": "Database name to check"
                    },
                    "schema": {
                        "type": "string",
                        "description": "Optional schema name to also verify within the database"
                    }
                },
                "required": ["database"]
            },
        )
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """
    Dispatch tool calls to the SnowflakeMCPServer instance.
    """
    try:
        if name == "execute_query":
            query = arguments.get("query")
            timeout_seconds = arguments.get("timeout_seconds")
            query_tag = arguments.get("query_tag")
            disable_cache = arguments.get("disable_cache", True)  # Default to True
            
            if not query:
                raise ValueError("Query is required")

            # Validate timeout parameter if provided
            if timeout_seconds is not None:
                if not isinstance(timeout_seconds, int) or timeout_seconds < 1 or timeout_seconds > 3600:
                    raise ValueError("Timeout must be an integer between 1 and 3600 seconds")
            
            # Validate query is read-only
            is_valid, error_message = QueryValidator.is_read_only_query(query)
            if not is_valid:
                raise ValueError(f"Query validation failed: {error_message}")
            
            # Execute the query
            result = await snowflake_server.execute_query(
                query=query,
                timeout_seconds=timeout_seconds,
                query_tag=query_tag,
                disable_cache=disable_cache
            )
            
            # Format results for display (matching sophisticated server format)
            output = f"Query executed successfully!\n\n"
            
            # Show query ID (most important for performance analysis)
            if result.get('query_id'):
                output += f"Query ID: {result['query_id']}\n"
            
            # Show query tag
            output += f"Query tag: {result['query_tag']}\n"
            
            # Show cache status
            cache_status = "DISABLED" if disable_cache else "ENABLED"
            output += f"Result cache: {cache_status}\n"
            
            # Show timeout information
            actual_timeout = timeout_seconds if timeout_seconds is not None else snowflake_server.snowflake_config.timeout
            output += f"Timeout: {actual_timeout} seconds ({actual_timeout/60:.1f} minutes)\n"
            output += f"Columns: {', '.join(result['columns'])}\n"
            output += f"Rows returned: {result['row_count']}\n"
            
            if result['has_more_rows']:
                output += f"⚠️  Results limited to {result['max_rows_returned']} rows. Query returned more data.\n"
            
            output += "\nResults:\n"
            output += json.dumps(result['rows'], indent=2, default=str)
            
            return [types.TextContent(type="text", text=output)]

        elif name == "list_databases":
            query = "SHOW DATABASES"
            result = await snowflake_server.execute_query(
                query=query,
            )

            databases = [row.get('name', '') for row in result['rows']]
            output = f"Available databases ({len(databases)}):\n"
            output += "\n".join(f"• {db}" for db in databases)

            return [types.TextContent(type="text", text=output)]

        elif name == "list_schemas":
            database = arguments.get("database")
            if not database:
                raise ValueError("Database is required")

            query = f"SHOW SCHEMAS IN DATABASE {database}"
            result = await snowflake_server.execute_query(
                query=query,
            )
            schemas = [row.get('name', '') for row in result['rows']]
            output = f"Available schemas ({len(schemas)}) in database {database}:\n"
            output += "\n".join(f"• {schema}" for schema in schemas)
            return [types.TextContent(type="text", text=output)]

        elif name == "list_tables":
            database = arguments.get("database")
            schema = arguments.get("schema")
            if not database or not schema:
                raise ValueError("Both database and schema names are required")
            
            query = f"SHOW TABLES IN SCHEMA {database}.{schema}"
            result = await snowflake_server.execute_query(query=query)
            
            tables = []
            for row in result['rows']:
                table_info = f"• {row.get('name', '')} ({row.get('kind', 'TABLE')})"
                if row.get('comment'):
                    table_info += f" - {row.get('comment')}"
                tables.append(table_info)
            
            output = f"Tables in {database}.{schema} ({len(tables)}):\n"
            output += "\n".join(tables)
            
            return [types.TextContent(type="text", text=output)]

        elif name == "describe_table":
            database = arguments.get("database")
            schema = arguments.get("schema")
            table = arguments.get("table")
            if not database or not schema or not table:
                raise ValueError("Both database, schema and table names are required")
            
            query = f"DESCRIBE TABLE {database}.{schema}.{table}"
            result = await snowflake_server.execute_query(query=query)

            # 1. Header with table name
            output = f"Structure of table {database}.{schema}.{table}:\n\n"
            
            # 2. Column headers (with fixed widths for alignment)
            output += f"{'Column':<30} {'Type':<20} {'Null?':<8} {'Default':<15} {'Comment'}\n"
            
            # 3. Separator line
            output += "-" * 90 + "\n"
            
            # 4. Loop through each row
            for row in result['rows']:
                name = str(row.get('name', ''))[:29]           # Truncate to fit
                data_type = str(row.get('type', ''))[:19]
                nullable = 'YES' if row.get('null?') == 'Y' else 'NO'
                default = str(row.get('default', '') or '')[:14]
                comment = str(row.get('comment', '') or '')
                
                output += f"{name:<30} {data_type:<20} {nullable:<8} {default:<15} {comment}\n"
            
            # 5. Return
            return [types.TextContent(type="text", text=output)]

        elif name == "check_database_exists":
            database = arguments.get("database")
            schema = arguments.get("schema")  # Optional
            if not database:
                raise ValueError("Database name is required")
            
            # Test database access by listing schemas
            try:
                test_query = f"SHOW SCHEMAS IN DATABASE {database}"
                result = await snowflake_server.execute_query(test_query)
                schema_count = len(result['rows'])
                
                output = f"✅ Database '{database}' exists and is accessible.\n"
                output += f"   Found {schema_count} schemas in this database.\n\n"
                
                # If schema provided, also test schema access
                if schema:
                    try:
                        schema_test = f"SHOW TABLES IN SCHEMA {database}.{schema}"
                        schema_result = await snowflake_server.execute_query(schema_test)
                        table_count = len(schema_result['rows'])
                        output += f"✅ Schema '{schema}' is accessible with {table_count} tables.\n\n"
                    except Exception as e:
                        output += f"⚠️  Schema '{schema}' may not be accessible: {str(e)}\n\n"
                
                output += f"💡 To query this database, use fully qualified names like:\n"
                output += f"   SELECT * FROM {database}.schema_name.table_name"
                
                return [types.TextContent(type="text", text=output)]
                
            except Exception as e:
                error_msg = f"❌ Cannot access database '{database}': {str(e)}"
                return [types.TextContent(type="text", text=error_msg)]

        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        error_msg = f"Error executing {name}: {str(e)}"
        logger.error(error_msg)
        return [types.TextContent(type="text", text=error_msg)]
            



# ---------------------------------------------------------------------------
# Entry point (async stdio transport)
# ---------------------------------------------------------------------------

async def main() -> None:
    """Main entry point for the server."""
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
