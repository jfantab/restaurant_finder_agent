"""Google Places MCP toolset wrapper for Cloud Run deployment."""

import os
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import SseConnectionParams


def get_google_places_cloud_toolset(server_url: str = None):
    """Returns Google Places MCP toolset connected to Cloud Run deployment.

    Args:
        server_url: Optional Cloud Run service URL. If not provided, reads from
                   GOOGLE_PLACES_MCP_URL environment variable.

    Returns:
        McpToolset: Configured Google Places MCP tools including:
            - search_places: Search for restaurants and places
            - get_place_details: Get detailed info about a specific place
            - search_nearby: Find places near coordinates
            - autocomplete_places: Get autocomplete suggestions
            - geocode_address: Convert addresses to coordinates

    Raises:
        ValueError: If server URL is not provided

    Example:
        # Set environment variable
        export GOOGLE_PLACES_MCP_URL="https://google-places-mcp-xxxxx-uw.a.run.app/sse"

        # Or pass directly
        toolset = get_google_places_cloud_toolset(
            "https://google-places-mcp-xxxxx-uw.a.run.app/sse"
        )
    """
    # Get server URL from parameter or environment
    mcp_url = server_url or os.getenv("GOOGLE_PLACES_MCP_URL")

    if not mcp_url:
        raise ValueError(
            "Google Places MCP server URL not provided. Either:\n"
            "  1. Pass server_url parameter\n"
            "  2. Set GOOGLE_PLACES_MCP_URL environment variable\n\n"
            "Example URL: https://google-places-mcp-xxxxx-uw.a.run.app/sse"
        )

    # Ensure URL ends with /sse
    if not mcp_url.endswith("/sse"):
        mcp_url = f"{mcp_url.rstrip('/')}/sse"

    # Configure Google Places MCP toolset with SSE connection
    return McpToolset(
        connection_params=SseConnectionParams(
            url=mcp_url,
            timeout=30,
        ),
    )
