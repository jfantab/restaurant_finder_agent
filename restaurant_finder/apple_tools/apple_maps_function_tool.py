"""Apple Maps FunctionTools for Vertex AI deployment.

This module provides pickle-safe FunctionTools that call the Apple Maps API
directly, making them compatible with Vertex AI Agent Engine deployment.

Unlike McpToolset which uses subprocess/stdio connections (not pickleable),
these tools make direct HTTP calls to the Apple Maps MCP server on Cloud Run.
"""

import os
import requests
from google.adk.tools import FunctionTool


def search_places(query: str, limit: int = 5) -> str:
    """
    Search for places using Apple Maps via Cloud Run MCP server.

    This tool searches Apple Maps for locations, businesses, and points of interest
    based on a natural language query. Results include business names and addresses.

    Args:
        query: Natural language search query (e.g., "Thai restaurants in Queens NY",
               "coffee shops near Central Park", "museums in San Francisco")
        limit: Maximum number of results to return (default: 5, max: 20)

    Returns:
        Formatted string with search results, one per line, or error message
    """
    try:
        # Get MCP server URL from environment
        mcp_base_url = os.getenv("APPLE_MAPS_MCP_URL", "")
        if not mcp_base_url:
            return "Error: APPLE_MAPS_MCP_URL environment variable not set"

        # Remove /sse suffix if present to get base URL
        mcp_base_url = mcp_base_url.replace("/sse", "")

        # Call the MCP server's search endpoint
        # Note: This is a direct HTTP call, bypassing the MCP protocol
        # The MCP server should expose a REST API endpoint for this
        response = requests.post(
            f"{mcp_base_url}/api/search_places",
            json={"query": query, "limit": limit},
            timeout=30
        )
        response.raise_for_status()

        result = response.json()
        return result.get("result", "No results found")

    except requests.exceptions.Timeout:
        return "Error: Request to Apple Maps MCP server timed out"
    except requests.exceptions.RequestException as e:
        return f"Error calling Apple Maps MCP server: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


def get_place_details(place_name: str, address: str) -> str:
    """
    Get detailed information about a specific place using Apple Maps.

    This tool searches for a specific place by name and address to get comprehensive
    details including exact location, contact information, and other metadata.

    Args:
        place_name: Name of the place/restaurant (e.g., "Osha Thai", "Blue Bottle Coffee")
        address: Street address of the place (e.g., "4 Embarcadero Center, San Francisco, CA")

    Returns:
        Formatted string with detailed place information
    """
    try:
        mcp_base_url = os.getenv("APPLE_MAPS_MCP_URL", "")
        if not mcp_base_url:
            return "Error: APPLE_MAPS_MCP_URL environment variable not set"

        mcp_base_url = mcp_base_url.replace("/sse", "")

        response = requests.post(
            f"{mcp_base_url}/api/get_place_details",
            json={"place_name": place_name, "address": address},
            timeout=30
        )
        response.raise_for_status()

        result = response.json()
        return result.get("result", "No details found")

    except requests.exceptions.Timeout:
        return "Error: Request to Apple Maps MCP server timed out"
    except requests.exceptions.RequestException as e:
        return f"Error calling Apple Maps MCP server: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


def geocode_address(address: str) -> str:
    """
    Convert an address to geographic coordinates using Apple Maps.

    Args:
        address: Street address to geocode (e.g., "1 Apple Park Way, Cupertino, CA")

    Returns:
        Formatted string with location details including coordinates
    """
    try:
        mcp_base_url = os.getenv("APPLE_MAPS_MCP_URL", "")
        if not mcp_base_url:
            return "Error: APPLE_MAPS_MCP_URL environment variable not set"

        mcp_base_url = mcp_base_url.replace("/sse", "")

        response = requests.post(
            f"{mcp_base_url}/api/geocode_address",
            json={"address": address},
            timeout=30
        )
        response.raise_for_status()

        result = response.json()
        return result.get("result", "No location found")

    except requests.exceptions.Timeout:
        return "Error: Request to Apple Maps MCP server timed out"
    except requests.exceptions.RequestException as e:
        return f"Error calling Apple Maps MCP server: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


# Create FunctionTool instances (these are pickleable!)
search_places_tool = FunctionTool(search_places)
get_place_details_tool = FunctionTool(get_place_details)
geocode_address_tool = FunctionTool(geocode_address)


def get_apple_maps_function_tools():
    """Returns list of Apple Maps FunctionTools for deployment.

    These tools work in both local development and Vertex AI deployment,
    unlike MCP toolsets which are not pickleable.

    Returns:
        List of FunctionTool instances for Apple Maps API
    """
    return [
        search_places_tool,
        get_place_details_tool,
        geocode_address_tool,
    ]
