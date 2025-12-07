"""Google Places MCP toolset wrapper for Google ADK agents."""

import os
from pathlib import Path
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters


def get_google_places_toolset():
    """Returns configured Google Places MCP toolset for restaurant search.

    Returns:
        McpToolset: Configured Google Places MCP tools including:
            - search_places: Search for restaurants and places
            - get_place_details: Get detailed information about a place
            - search_nearby: Find places near coordinates
            - autocomplete_places: Get autocomplete suggestions
            - geocode_address: Convert addresses to coordinates

    Raises:
        ValueError: If required Google Places API key is not set
    """
    # Load Google Maps API key from environment
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")

    if not api_key:
        raise ValueError(
            "Google Maps API key not found. Required environment variable:\n"
            "  - GOOGLE_MAPS_API_KEY"
        )

    # Get the path to the google_places_mcp.py script
    tools_dir = Path(__file__).parent
    google_places_script = tools_dir / "google_places_mcp.py"

    if not google_places_script.exists():
        raise FileNotFoundError(
            f"Google Places MCP script not found at {google_places_script}"
        )

    # Configure Google Places MCP toolset
    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="python",
                args=[str(google_places_script)],
                env={
                    "GOOGLE_MAPS_API_KEY": api_key,
                }
            ),
            timeout=30,
        ),
    )
