#!/usr/bin/env python3
"""
Google Places API MCP Server

This MCP server exposes Google Places API functionality as tools that can be
used by AI agents through the Model Context Protocol.

Features:
- Place search (text search, nearby search)
- Place details retrieval
- Autocomplete functionality
- Place photos access
- Clean result formatting optimized for LLM consumption
- Error handling with informative messages

Run as MCP server:
    python google_places_mcp.py

Environment variables required:
- GOOGLE_MAPS_API_KEY: Your Google Maps API key
"""

import os
import requests
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Load environment variables
load_dotenv()

# Initialize the MCP Server
mcp = FastMCP("GooglePlaces")

# Configuration
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
BASE_URL = "https://places.googleapis.com/v1"


def _make_request(
    endpoint: str,
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    json_data: Optional[Dict[str, Any]] = None,
    method: str = "GET"
) -> Dict[str, Any]:
    """
    Make a request to the Google Places API.

    Args:
        endpoint: API endpoint path
        headers: Optional HTTP headers
        params: Optional query parameters
        json_data: Optional JSON body for POST requests
        method: HTTP method (GET or POST)

    Returns:
        JSON response as dictionary

    Raises:
        RuntimeError: If API key is not configured or request fails
    """
    if not API_KEY:
        raise RuntimeError(
            "GOOGLE_MAPS_API_KEY must be set in environment variables"
        )

    url = f"{BASE_URL}/{endpoint}"
    default_headers = {
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": "*"  # Request all available fields
    }

    if headers:
        default_headers.update(headers)

    try:
        if method == "POST":
            resp = requests.post(
                url,
                headers=default_headers,
                json=json_data,
                params=params,
                timeout=10
            )
        else:
            resp = requests.get(
                url,
                headers=default_headers,
                params=params,
                timeout=10
            )

        resp.raise_for_status()
        return resp.json()

    except requests.exceptions.Timeout:
        raise RuntimeError("Request to Google Places API timed out")
    except requests.exceptions.HTTPError as e:
        error_msg = f"Google Places API error: {e.response.status_code}"
        try:
            error_detail = e.response.json()
            if "error" in error_detail:
                error_msg += f" - {error_detail['error'].get('message', '')}"
        except:
            pass
        raise RuntimeError(error_msg)
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Error calling Google Places API: {str(e)}")


def _format_place(place: Dict[str, Any], include_details: bool = False) -> str:
    """
    Format a place result for LLM consumption.

    Args:
        place: Place data from API response
        include_details: Whether to include detailed information

    Returns:
        Formatted string representation of the place
    """
    name = place.get("displayName", {}).get("text", "Unknown")
    address = place.get("formattedAddress", "No address")
    place_id = place.get("id", "")

    parts = [f"Name: {name}", f"Address: {address}"]

    # Always include Place ID so agents can fetch details later
    if place_id:
        parts.append(f"Place ID: {place_id}")

    # Always include location coordinates (critical for map display)
    location = place.get("location")
    if location:
        lat = location.get("latitude")
        lon = location.get("longitude")
        if lat is not None and lon is not None:
            # Use explicit labels for easier parsing by LLM
            parts.append(f"Latitude: {lat}")
            parts.append(f"Longitude: {lon}")

    if include_details:
        # Rating and reviews
        rating = place.get("rating")
        user_ratings = place.get("userRatingCount")
        if rating:
            rating_str = f"Rating: {rating:.1f}"
            if user_ratings:
                rating_str += f" ({user_ratings} reviews)"
            parts.append(rating_str)

        # Phone number
        phone = place.get("internationalPhoneNumber") or place.get("nationalPhoneNumber")
        if phone:
            parts.append(f"Phone: {phone}")

        # Website
        website = place.get("websiteUri")
        if website:
            parts.append(f"Website: {website}")

        # Current open/closed status
        if "currentOpeningHours" in place:
            current_hours = place["currentOpeningHours"]
            is_open = current_hours.get("openNow")
            if is_open is not None:
                parts.append(f"Currently Open: {'Yes' if is_open else 'No'}")

        # Business hours
        if "regularOpeningHours" in place:
            hours = place["regularOpeningHours"]
            if "weekdayDescriptions" in hours:
                parts.append("Hours:")
                for desc in hours["weekdayDescriptions"]:
                    parts.append(f"  {desc}")

        # Price level - convert to $ symbols for easier use
        price_level = place.get("priceLevel")
        if price_level:
            price_map = {
                "PRICE_LEVEL_FREE": "Free",
                "PRICE_LEVEL_INEXPENSIVE": "$",
                "PRICE_LEVEL_MODERATE": "$$",
                "PRICE_LEVEL_EXPENSIVE": "$$$",
                "PRICE_LEVEL_VERY_EXPENSIVE": "$$$$"
            }
            price_display = price_map.get(price_level, price_level)
            parts.append(f"Price Level: {price_display}")

        # Types/Categories
        types = place.get("types", [])
        if types:
            # Filter out generic types and keep only meaningful ones
            meaningful_types = [t for t in types if not t.startswith("point_of_interest")]
            if meaningful_types:
                parts.append(f"Categories: {', '.join(meaningful_types[:5])}")

        # Google Maps link
        if location:
            lat = location.get("latitude")
            lon = location.get("longitude")
            if lat is not None and lon is not None:
                parts.append(f"Google Maps: https://www.google.com/maps/search/?api=1&query={lat},{lon}")

    return "\n".join(parts)


@mcp.tool()
def search_places(
    query: str,
    location: Optional[str] = None,
    radius_meters: int = 5000,
    limit: int = 5
) -> str:
    """
    Search for places using Google Places API text search.

    This tool searches Google Places for locations, businesses, and points of interest
    based on a natural language query.

    Args:
        query: Natural language search query (e.g., "Thai restaurants", "coffee shops",
               "museums in San Francisco")
        location: Optional location to center search (e.g., "New York, NY", "37.7749,-122.4194").
                 Can be an address or coordinates.
        radius_meters: Search radius in meters (default: 5000, max: 50000)
        limit: Maximum number of results to return (default: 5, max: 20)

    Returns:
        Formatted string with search results or error message
    """
    if not query or not query.strip():
        return "Error: Query cannot be empty"

    limit = max(1, min(limit, 20))
    radius_meters = max(100, min(radius_meters, 50000))

    try:
        # Build request body
        request_body = {
            "textQuery": query.strip(),
            "pageSize": limit
        }

        # Add location bias if provided
        if location:
            # Try to geocode the location first if it's not coordinates
            if "," in location and all(part.replace(".", "").replace("-", "").isdigit()
                                       for part in location.split(",")):
                # It's coordinates
                lat, lon = map(float, location.split(","))
                request_body["locationBias"] = {
                    "circle": {
                        "center": {"latitude": lat, "longitude": lon},
                        "radius": radius_meters
                    }
                }
            else:
                # It's an address, include in query
                request_body["textQuery"] = f"{query.strip()} in {location}"

        # Make API request
        data = _make_request(
            "places:searchText",
            method="POST",
            json_data=request_body
        )

        places = data.get("places", [])

        if not places:
            return f"No results found for '{query}'"

        # Format results
        formatted = []
        for i, place in enumerate(places[:limit], 1):
            formatted.append(f"{i}. {_format_place(place, include_details=False)}")

        result_text = "\n\n".join(formatted)
        return f"Found {len(places)} results for '{query}':\n\n{result_text}"

    except RuntimeError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@mcp.tool()
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
    if not place_id or not place_id.strip():
        return "Error: Place ID cannot be empty"

    try:
        # Make API request
        data = _make_request(f"places/{place_id.strip()}")

        if not data:
            return f"No details found for place ID: {place_id}"

        # Format detailed response
        result = _format_place(data, include_details=True)

        # Add reviews if available
        reviews = data.get("reviews", [])
        if reviews:
            result += "\n\nRecent Reviews:"
            for i, review in enumerate(reviews[:3], 1):
                rating = review.get("rating", "N/A")
                text = review.get("text", {}).get("text", "")
                author = review.get("authorAttribution", {}).get("displayName", "Anonymous")
                result += f"\n\n{i}. {author} - {rating}⭐\n{text[:200]}{'...' if len(text) > 200 else ''}"

        return result

    except RuntimeError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@mcp.tool()
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
        place_type: Optional place type filter (e.g., "restaurant", "cafe", "museum").
                   See Google Places API docs for full list of types.
        keyword: Optional keyword to filter results (e.g., "thai", "outdoor seating")
        radius_meters: Search radius in meters (default: 1000, max: 50000)
        limit: Maximum number of results to return (default: 10, max: 20)

    Returns:
        Formatted string with nearby places
    """
    try:
        limit = max(1, min(limit, 20))
        radius_meters = max(100, min(radius_meters, 50000))

        # Build request body
        request_body = {
            "locationRestriction": {
                "circle": {
                    "center": {
                        "latitude": latitude,
                        "longitude": longitude
                    },
                    "radius": radius_meters
                }
            },
            "maxResultCount": limit
        }

        # Add filters if provided
        if place_type:
            request_body["includedTypes"] = [place_type]

        # Note: searchNearby does not support textQuery or keyword filtering
        # Only type-based filtering is supported
        # If keyword is needed, use search_places with textQuery instead

        # Make API request
        data = _make_request(
            "places:searchNearby",
            method="POST",
            json_data=request_body
        )

        places = data.get("places", [])

        if not places:
            location_desc = f"({latitude}, {longitude})"
            filters = []
            if place_type:
                filters.append(f"type: {place_type}")
            filter_desc = " with " + ", ".join(filters) if filters else ""
            return f"No places found near {location_desc}{filter_desc}"

        # Format results
        formatted = []
        for i, place in enumerate(places[:limit], 1):
            formatted.append(f"{i}. {_format_place(place, include_details=False)}")

        result_text = "\n\n".join(formatted)
        filter_info = []
        if place_type:
            filter_info.append(f"type: {place_type}")
        filter_str = f" ({', '.join(filter_info)})" if filter_info else ""

        return f"Found {len(places)} places within {radius_meters}m{filter_str}:\n\n{result_text}"

    except RuntimeError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@mcp.tool()
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
    if not input_text or not input_text.strip():
        return "Error: Input text cannot be empty"

    try:
        # Build request body
        request_body = {
            "input": input_text.strip()
        }

        # Note: locationBias requires circle or rectangle, not text
        # For simplicity, we'll omit locationBias and rely on IP biasing
        # To use locationBias properly, you'd need to geocode the location first

        # Make API request
        data = _make_request(
            "places:autocomplete",
            method="POST",
            json_data=request_body
        )

        suggestions = data.get("suggestions", [])

        if not suggestions:
            return f"No autocomplete suggestions found for '{input_text}'"

        # Format results
        formatted = []
        for i, suggestion in enumerate(suggestions[:10], 1):
            place_prediction = suggestion.get("placePrediction", {})
            text = place_prediction.get("text", {}).get("text", "Unknown")
            place_id = place_prediction.get("placeId", "")

            formatted.append(f"{i}. {text}")
            if place_id:
                formatted.append(f"   Place ID: {place_id}")

        result_text = "\n".join(formatted)
        return f"Autocomplete suggestions for '{input_text}':\n\n{result_text}"

    except RuntimeError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@mcp.tool()
def geocode_address(address: str) -> str:
    """
    Convert an address to geographic coordinates using Google Places Geocoding.

    Args:
        address: Street address to geocode (e.g., "1600 Amphitheatre Parkway, Mountain View, CA")

    Returns:
        Formatted string with location details including coordinates
    """
    if not address or not address.strip():
        return "Error: Address cannot be empty"

    try:
        # Use text search to geocode
        request_body = {
            "textQuery": address.strip(),
            "pageSize": 1
        }

        data = _make_request(
            "places:searchText",
            method="POST",
            json_data=request_body
        )

        places = data.get("places", [])

        if not places:
            return f"No location found for address: '{address}'"

        place = places[0]
        location = place.get("location", {})
        lat = location.get("latitude")
        lon = location.get("longitude")

        if lat is not None and lon is not None:
            name = place.get("displayName", {}).get("text", "Unknown")
            formatted_address = place.get("formattedAddress", "No address")

            return (
                f"Location: {name}\n"
                f"Address: {formatted_address}\n"
                f"Coordinates: {lat}, {lon}\n"
                f"Google Maps: https://www.google.com/maps/search/?api=1&query={lat},{lon}\n"
                f"Place ID: {place.get('id', 'N/A')}"
            )
        else:
            return f"Location found but coordinates not available"

    except RuntimeError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


# Main entry point
if __name__ == "__main__":
    # Run the MCP server
    # For Cloud Run, we just run normally and FastMCP handles everything
    # The PORT environment variable is automatically detected
    mcp.run()
