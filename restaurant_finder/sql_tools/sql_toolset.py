"""SQL Restaurant Database MCP toolset wrapper for Google ADK agents."""

import os
from pathlib import Path
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters


def get_sql_toolset():
    """Returns configured SQL Restaurant MCP toolset for restaurant search.

    This toolset connects to the local SQL MCP server via stdio, which queries
    the Neon PostgreSQL database for restaurant data.

    Returns:
        McpToolset: Configured SQL MCP tools including:
            - search_restaurants: Search for restaurants by location and filters
            - get_restaurant_reviews: Get reviews for a specific restaurant
            - get_restaurant_details: Get detailed information about a restaurant

    Raises:
        ValueError: If required NEON_DATABASE_URL is not set
    """
    # Verify database URL is configured
    database_url = os.getenv("NEON_DATABASE_URL")

    if not database_url:
        raise ValueError(
            "Neon database URL not found. Required environment variable:\n"
            "  - NEON_DATABASE_URL"
        )

    # Get the path to the sql_mcp.py script
    tools_dir = Path(__file__).parent
    sql_mcp_script = tools_dir / "sql_mcp.py"

    if not sql_mcp_script.exists():
        raise FileNotFoundError(
            f"SQL MCP script not found at {sql_mcp_script}"
        )

    # Configure SQL MCP toolset with stdio connection
    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="python",
                args=[str(sql_mcp_script)],
                env={
                    "NEON_DATABASE_URL": database_url,
                }
            ),
            timeout=30,
        ),
    )
