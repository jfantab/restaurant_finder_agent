"""Apple Maps MCP toolset wrapper for Google ADK agents."""

import os
from pathlib import Path
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters


def get_apple_maps_toolset():
    """Returns configured Apple Maps MCP toolset for restaurant search.

    Returns:
        McpToolset: Configured Apple Maps MCP tools including:
            - search_places: Search for restaurants and places
            - geocode_address: Convert addresses to coordinates

    Raises:
        ValueError: If required Apple Maps credentials are not set
    """
    # Load Apple Maps credentials from environment
    apple_team_id = os.getenv("APPLE_TEAM_ID")
    apple_key_id = os.getenv("APPLE_KEY_ID")
    apple_private_key = os.getenv("APPLE_PRIVATE_KEY")

    if not apple_team_id or not apple_key_id or not apple_private_key:
        raise ValueError(
            "Apple Maps credentials not found. Required environment variables:\n"
            "  - APPLE_TEAM_ID\n"
            "  - APPLE_KEY_ID\n"
            "  - APPLE_PRIVATE_KEY"
        )

    # Get the path to the apple_maps_mcp.py script
    tools_dir = Path(__file__).parent
    apple_maps_script = tools_dir / "apple_maps_mcp.py"

    if not apple_maps_script.exists():
        raise FileNotFoundError(
            f"Apple Maps MCP script not found at {apple_maps_script}"
        )

    # Configure Apple Maps MCP toolset
    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="python",
                args=[str(apple_maps_script)],
                env={
                    "APPLE_TEAM_ID": apple_team_id,
                    "APPLE_KEY_ID": apple_key_id,
                    "APPLE_PRIVATE_KEY": apple_private_key,
                }
            ),
            timeout=30,
        ),
    )
