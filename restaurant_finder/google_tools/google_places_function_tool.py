"""Google Places FunctionTools for Vertex AI deployment.

This module provides pickle-safe FunctionTools that call the Google Places API
directly, making them compatible with Vertex AI Agent Engine deployment.

Unlike McpToolset which uses subprocess/stdio connections (not pickleable),
these tools make direct HTTP calls to the Google Places MCP server on Cloud Run.
"""

import os
import requests
from google.adk.tools import FunctionTool
from typing import Optional


def search_places(
    query: str,
    location: Optional[str] = None,
    radius_meters: int = 5000,
    limit: int = 5
) -> str:
    """
    Search for places using Google Places API via Cloud Run MCP server.

    This tool searches Google Places for locations, businesses, and points of interest
    based on a natural language query.

    Args:
        query: Natural language search query (e.g., "Thai restaurants", "coffee shops",
               "museums in San Francisco")
        location: Optional location to center search (e.g., "New York, NY", "37.7749,-122.4194")
        radius_meters: Search radius in meters (default: 5000, max: 50000)
        limit: Maximum number of results to return (default: 5, max: 20)

    Returns:
        Formatted string with search results or error message
    """
    try:
        # Get MCP server URL from environment
        mcp_base_url = os.getenv("GOOGLE_PLACES_MCP_URL", "")
        if not mcp_base_url:
            return "Error: GOOGLE_PLACES_MCP_URL environment variable not set"

        # Remove /sse suffix if present to get base URL
        mcp_base_url = mcp_base_url.replace("/sse", "")

        # Call the MCP server's search endpoint
        response = requests.post(
            f"{mcp_base_url}/api/search_places",
            json={
                "query": query,
                "location": location,
                "radius_meters": radius_meters,
                "limit": limit
            },
            timeout=30
        )
        response.raise_for_status()

        result = response.json()
        return result.get("result", "No results found")

    except requests.exceptions.Timeout:
        return "Error: Request to Google Places MCP server timed out"
    except requests.exceptions.RequestException as e:
        return f"Error calling Google Places MCP server: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


def get_place_details(place_id: str) -> str:
    """
    Get detailed information about a specific place using its Google Place ID.

    This tool retrieves comprehensive details including hours, contact info, ratings,
    reviews, and more.

    Args:
        place_id: Google Place ID (e.g., "ChIJN1t_tDeuEmsRUsoyG83frY4")

    Returns:
        Formatted string with detailed place information
    """
    try:
        mcp_base_url = os.getenv("GOOGLE_PLACES_MCP_URL", "")
        if not mcp_base_url:
            return "Error: GOOGLE_PLACES_MCP_URL environment variable not set"

        mcp_base_url = mcp_base_url.replace("/sse", "")

        response = requests.post(
            f"{mcp_base_url}/api/get_place_details",
            json={"place_id": place_id},
            timeout=30
        )
        response.raise_for_status()

        result = response.json()
        return result.get("result", "No details found")

    except requests.exceptions.Timeout:
        return "Error: Request to Google Places MCP server timed out"
    except requests.exceptions.RequestException as e:
        return f"Error calling Google Places MCP server: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


def search_nearby(
    latitude: float,
    longitude: float,
    place_type: Optional[str] = None,
    keyword: Optional[str] = None,
    radius_meters: int = 1000,
    limit: int = 10
) -> str:
    """
    Search for places near a specific location using Google Places Nearby Search.

    Args:
        latitude: Latitude coordinate (e.g., 37.7749)
        longitude: Longitude coordinate (e.g., -122.4194)
        place_type: Optional place type filter (e.g., "restaurant", "cafe", "museum")
        keyword: Optional keyword to filter results (e.g., "thai", "outdoor seating")
        radius_meters: Search radius in meters (default: 1000, max: 50000)
        limit: Maximum number of results to return (default: 10, max: 20)

    Returns:
        Formatted string with nearby places
    """
    try:
        mcp_base_url = os.getenv("GOOGLE_PLACES_MCP_URL", "")
        if not mcp_base_url:
            return "Error: GOOGLE_PLACES_MCP_URL environment variable not set"

        mcp_base_url = mcp_base_url.replace("/sse", "")

        response = requests.post(
            f"{mcp_base_url}/api/search_nearby",
            json={
                "latitude": latitude,
                "longitude": longitude,
                "place_type": place_type,
                "keyword": keyword,
                "radius_meters": radius_meters,
                "limit": limit
            },
            timeout=30
        )
        response.raise_for_status()

        result = response.json()
        return result.get("result", "No places found")

    except requests.exceptions.Timeout:
        return "Error: Request to Google Places MCP server timed out"
    except requests.exceptions.RequestException as e:
        return f"Error calling Google Places MCP server: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


def autocomplete_places(input_text: str, location: Optional[str] = None) -> str:
    """
    Get place autocomplete suggestions based on user input.

    This tool provides autocomplete predictions for place searches, useful for
    helping users find specific places or getting place IDs.

    Args:
        input_text: The text to autocomplete (e.g., "Golden Gate", "Starbucks on Mai")
        location: Optional location to bias results (e.g., "San Francisco, CA")

    Returns:
        Formatted string with autocomplete suggestions
    """
    try:
        mcp_base_url = os.getenv("GOOGLE_PLACES_MCP_URL", "")
        if not mcp_base_url:
            return "Error: GOOGLE_PLACES_MCP_URL environment variable not set"

        mcp_base_url = mcp_base_url.replace("/sse", "")

        response = requests.post(
            f"{mcp_base_url}/api/autocomplete_places",
            json={
                "input_text": input_text,
                "location": location
            },
            timeout=30
        )
        response.raise_for_status()

        result = response.json()
        return result.get("result", "No suggestions found")

    except requests.exceptions.Timeout:
        return "Error: Request to Google Places MCP server timed out"
    except requests.exceptions.RequestException as e:
        return f"Error calling Google Places MCP server: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


def geocode_address(address: str) -> str:
    """
    Convert an address to geographic coordinates using Google Places Geocoding.

    Args:
        address: Street address to geocode (e.g., "1600 Amphitheatre Parkway, Mountain View, CA")

    Returns:
        Formatted string with location details including coordinates
    """
    try:
        mcp_base_url = os.getenv("GOOGLE_PLACES_MCP_URL", "")
        if not mcp_base_url:
            return "Error: GOOGLE_PLACES_MCP_URL environment variable not set"

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
        return "Error: Request to Google Places MCP server timed out"
    except requests.exceptions.RequestException as e:
        return f"Error calling Google Places MCP server: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


# Create FunctionTool instances (these are pickleable!)
search_places_tool = FunctionTool(search_places)
get_place_details_tool = FunctionTool(get_place_details)
search_nearby_tool = FunctionTool(search_nearby)
autocomplete_places_tool = FunctionTool(autocomplete_places)
geocode_address_tool = FunctionTool(geocode_address)


def get_google_places_function_tools():
    """Returns list of Google Places FunctionTools for deployment.

    These tools work in both local development and Vertex AI deployment,
    unlike MCP toolsets which are not pickleable.

    Returns:
        List of FunctionTool instances for Google Places API
    """
    return [
        search_places_tool,
        get_place_details_tool,
        search_nearby_tool,
        autocomplete_places_tool,
        geocode_address_tool,
    ]
