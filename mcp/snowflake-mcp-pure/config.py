"""
Configuration models for Snowflake MCP Server.

Provides type-safe configuration management using Pydantic models
with environment variable integration.
"""

import os
from typing import Optional

from pydantic import BaseModel, Field
from dotenv import load_dotenv


class SnowflakeConfig(BaseModel):
    """Configuration model for Snowflake connection using password authentication."""
    
    account: str = Field(..., description="Snowflake account identifier")
    user: str = Field(..., description="Snowflake username")
    password: str = Field(..., description="Snowflake password")
    warehouse: Optional[str] = Field(None, description="Default warehouse")
    database: Optional[str] = Field(None, description="Default database") 
    schema_name: Optional[str] = Field(None, description="Default schema")
    role: Optional[str] = Field(None, description="Default role")
    timeout: int = Field(30, description="Default query timeout in seconds")
    
    @classmethod
    def from_env(cls) -> "SnowflakeConfig":
        """Create configuration from environment variables.
        
        Required environment variables:
        - SNOWFLAKE_ACCOUNT
        - SNOWFLAKE_USER
        - SNOWFLAKE_PASSWORD
        
        Optional environment variables:
        - SNOWFLAKE_WAREHOUSE
        - SNOWFLAKE_DATABASE
        - SNOWFLAKE_SCHEMA
        - SNOWFLAKE_ROLE
        - SNOWFLAKE_TIMEOUT (default: 30)
        """
        # Load environment variables from .env file
        load_dotenv()
        
        account = os.getenv("SNOWFLAKE_ACCOUNT", "")
        user = os.getenv("SNOWFLAKE_USER", "")
        password = os.getenv("SNOWFLAKE_PASSWORD", "")
        
        if not account:
            raise RuntimeError("Missing required environment variable: SNOWFLAKE_ACCOUNT")
        if not user:
            raise RuntimeError("Missing required environment variable: SNOWFLAKE_USER")
        if not password:
            raise RuntimeError("Missing required environment variable: SNOWFLAKE_PASSWORD")
        
        return cls(
            account=account,
            user=user,
            password=password,
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
            database=os.getenv("SNOWFLAKE_DATABASE"),
            schema_name=os.getenv("SNOWFLAKE_SCHEMA"),
            role=os.getenv("SNOWFLAKE_ROLE"),
            timeout=int(os.getenv("SNOWFLAKE_TIMEOUT", "30")),
        )
    
    def to_connection_params(self) -> dict:
        """Convert to Snowflake connector parameters."""
        params = {
            "account": self.account,
            "user": self.user,
            "password": self.password,
            "client_session_keep_alive": True,
        }
        
        # Add optional parameters if they exist
        if self.warehouse:
            params["warehouse"] = self.warehouse
        if self.database:
            params["database"] = self.database
        if self.schema_name:
            params["schema"] = self.schema_name
        if self.role:
            params["role"] = self.role
            
        return params


class ServerConfig(BaseModel):
    """Configuration for the MCP server itself."""
    
    log_level: str = Field("INFO", description="Logging level")
    max_query_rows: int = Field(10000, description="Maximum rows to return from queries")
    
    @classmethod
    def from_env(cls) -> "ServerConfig":
        """Create server configuration from environment variables."""
        # Load environment variables from .env file
        load_dotenv()
        
        return cls(
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            max_query_rows=int(os.getenv("MAX_QUERY_ROWS", "10000")),
        )
