#!/usr/bin/env python3
"""
Apple Maps MCP Server

This MCP server exposes Apple Maps search functionality as a tool that can be
used by AI agents through the Model Context Protocol.

Features:
- Automatic JWT token generation and refresh
- Access token caching to minimize API calls
- Clean result formatting optimized for LLM consumption
- Error handling with informative messages

Run as MCP server:
    python apple_maps_mcp.py

Environment variables required:
- APPLE_TEAM_ID: Your Apple Team ID (10 characters)
- APPLE_KEY_ID: Your Maps Server API Key ID (10 characters)
- APPLE_PRIVATE_KEY: Base64-encoded private key OR path to .p8 file
"""

import os
import time
import jwt
import base64
import requests
from functools import lru_cache
from pathlib import Path
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Load environment variables
load_dotenv()

# Initialize the MCP Server
mcp = FastMCP("AppleMaps")

# Configuration
TEAM_ID = os.getenv("APPLE_TEAM_ID")
KEY_ID = os.getenv("APPLE_KEY_ID")
PRIVATE_KEY_BASE64 = os.getenv("APPLE_PRIVATE_KEY")
PRIVATE_KEY_PATH = os.getenv("APPLE_PRIVATE_KEY_PATH")


def decode_private_key_from_base64(base64_key: str) -> str:
    """
    Decode base64-encoded private key and format it as PEM.

    Args:
        base64_key: Base64-encoded private key

    Returns:
        PEM-formatted private key string
    """
    # Decode base64
    key_bytes = base64.b64decode(base64_key)

    # Convert to PEM format
    pem_key = "-----BEGIN PRIVATE KEY-----\n"
    # Split base64 into 64-character lines
    base64_str = base64.b64encode(key_bytes).decode('utf-8')
    for i in range(0, len(base64_str), 64):
        pem_key += base64_str[i:i+64] + "\n"
    pem_key += "-----END PRIVATE KEY-----\n"

    return pem_key


def load_private_key_from_file(key_path: str) -> str:
    """Load the private key from .p8 file."""
    with open(key_path, 'r') as f:
        return f.read()


def get_private_key() -> str:
    """
    Get the private key from environment variables or file.

    Returns:
        PEM-formatted private key string

    Raises:
        ValueError: If private key cannot be loaded
    """
    if PRIVATE_KEY_BASE64:
        try:
            return decode_private_key_from_base64(PRIVATE_KEY_BASE64)
        except Exception as e:
            raise ValueError(f"Failed to decode APPLE_PRIVATE_KEY: {e}")

    if PRIVATE_KEY_PATH and Path(PRIVATE_KEY_PATH).exists():
        try:
            return load_private_key_from_file(PRIVATE_KEY_PATH)
        except Exception as e:
            raise ValueError(f"Failed to load private key from file: {e}")

    raise ValueError(
        "Private key not found. Set either APPLE_PRIVATE_KEY (base64) "
        "or APPLE_PRIVATE_KEY_PATH (file path) in .env"
    )


@lru_cache(maxsize=1)
def _get_cached_access_token(ttl_hash: int = None) -> str:
    """
    Internal helper: Generates an Apple Maps Access Token.
    Cached based on 'ttl_hash' to prevent regenerating per request.

    This implements the two-step authentication:
    1. Generate JWT auth token using private key
    2. Exchange JWT for access token from Apple's API

    Args:
        ttl_hash: Cache key that rotates based on time

    Returns:
        Apple Maps access token string

    Raises:
        RuntimeError: If token generation fails
    """
    if not TEAM_ID or not KEY_ID:
        raise RuntimeError(
            "APPLE_TEAM_ID and APPLE_KEY_ID must be set in environment variables"
        )

    try:
        private_key = get_private_key()
    except ValueError as e:
        raise RuntimeError(str(e))

    # Step 1: Create the JWT auth token (The "Identity Card")
    headers = {
        "alg": "ES256",
        "kid": KEY_ID,
        "typ": "JWT"
    }

    payload = {
        "iss": TEAM_ID,
        "iat": int(time.time()),
        "exp": int(time.time() + 1800)  # 30 minutes
    }

    try:
        auth_token = jwt.encode(
            payload,
            private_key,
            algorithm="ES256",
            headers=headers
        )
    except Exception as e:
        raise RuntimeError(
            f"JWT signing failed. Check your private key format. Error: {e}"
        )

    # Step 2: Exchange JWT for Access Token (The "Event Ticket")
    url = "https://maps-api.apple.com/v1/token"
    try:
        token_resp = requests.get(
            url,
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=10
        )
        token_resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Failed to exchange JWT for access token: {e}")

    access_token = token_resp.json().get("accessToken")
    if not access_token:
        raise RuntimeError("No access token in response from Apple Maps API")

    return access_token


def get_token() -> str:
    """
    Get a valid Apple Maps access token.

    Uses caching with automatic refresh every 25 minutes to ensure
    the token is always valid (tokens expire after 30 minutes).

    Returns:
        Valid Apple Maps access token
    """
    # Rotates cache key every 25 mins (1500 sec) so we always have a valid token
    ttl_hash = int(time.time() / 1500)
    return _get_cached_access_token(ttl_hash=ttl_hash)


@mcp.tool()
def search_places(query: str, limit: int = 5) -> str:
    """
    Search for places using Apple Maps.

    This tool searches Apple Maps for locations, businesses, and points of interest
    based on a natural language query. Results include business names and addresses.

    Args:
        query: Natural language search query (e.g., "Thai restaurants in Queens NY",
               "coffee shops near Central Park", "museums in San Francisco")
        limit: Maximum number of results to return (default: 5, max: 20)

    Returns:
        Formatted string with search results, one per line, or error message
    """
    # Validate inputs
    if not query or not query.strip():
        return "Error: Query cannot be empty"

    limit = max(1, min(limit, 20))  # Clamp between 1 and 20

    try:
        # Get access token (cached)
        token = get_token()

        # Make search request
        url = "https://maps-api.apple.com/v1/search"
        headers = {"Authorization": f"Bearer {token}"}
        params = {
            "q": query.strip(),
            "lang": "en-US",
            "limitToCountries": "US"
        }

        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()

        # Parse and format results
        results = resp.json().get("results", [])

        if not results:
            return f"No results found for '{query}'"

        # Format results for LLM consumption
        formatted = []
        for i, place in enumerate(results[:limit], 1):
            name = place.get("name", "Unknown")
            address_lines = place.get("formattedAddressLines", [])
            address = ", ".join(address_lines) if address_lines else "No address"

            # Include phone number if available
            phone = place.get("phoneNumber", "")
            phone_str = f" | Phone: {phone}" if phone else ""

            formatted.append(f"{i}. {name}\n   Address: {address}{phone_str}")

        result_text = "\n\n".join(formatted)
        return f"Found {len(results)} results for '{query}':\n\n{result_text}"

    except RuntimeError as e:
        return f"Authentication error: {str(e)}"
    except requests.exceptions.Timeout:
        return "Error: Request to Apple Maps API timed out"
    except requests.exceptions.RequestException as e:
        return f"Error calling Apple Maps API: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@mcp.tool()
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
    if not place_name or not place_name.strip():
        return "Error: Place name cannot be empty"
    if not address or not address.strip():
        return "Error: Address cannot be empty"

    try:
        # Get access token (cached)
        token = get_token()

        # Construct a specific search query combining name and address
        query = f"{place_name.strip()}, {address.strip()}"

        # Make search request
        url = "https://maps-api.apple.com/v1/search"
        headers = {"Authorization": f"Bearer {token}"}
        params = {
            "q": query,
            "lang": "en-US",
        }

        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()

        # Parse results
        results = resp.json().get("results", [])

        if not results:
            return f"No details found for '{place_name}' at {address}"

        # Get the first (most relevant) result
        place = results[0]
        name = place.get("name", "Unknown")
        address_lines = place.get("formattedAddressLines", [])
        formatted_address = ", ".join(address_lines) if address_lines else "No address"

        # Extract coordinates
        coordinate = place.get("coordinate", {})
        lat = coordinate.get("latitude")
        lon = coordinate.get("longitude")

        # Extract additional details
        phone = place.get("phoneNumber", "")
        categories = place.get("categories", [])

        # Build detailed response
        details = [
            f"Name: {name}",
            f"Address: {formatted_address}",
        ]

        if phone:
            details.append(f"Phone: {phone}")

        if lat is not None and lon is not None:
            details.append(f"Coordinates: {lat}, {lon}")
            details.append(f"Maps Link: https://maps.google.com/?q={lat},{lon}")

        if categories:
            details.append(f"Categories: {', '.join(categories)}")

        return "\n".join(details)

    except RuntimeError as e:
        return f"Authentication error: {str(e)}"
    except requests.exceptions.Timeout:
        return "Error: Request to Apple Maps API timed out"
    except requests.exceptions.RequestException as e:
        return f"Error calling Apple Maps API: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@mcp.tool()
def geocode_address(address: str) -> str:
    """
    Convert an address to geographic coordinates using Apple Maps.

    Args:
        address: Street address to geocode (e.g., "1 Apple Park Way, Cupertino, CA")

    Returns:
        Formatted string with location details including coordinates
    """
    if not address or not address.strip():
        return "Error: Address cannot be empty"

    try:
        # Get access token (cached)
        token = get_token()

        # Make geocoding request
        url = "https://maps-api.apple.com/v1/geocode"
        headers = {"Authorization": f"Bearer {token}"}
        params = {
            "q": address.strip(),
            "lang": "en-US"
        }

        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()

        # Parse results
        results = resp.json().get("results", [])

        if not results:
            return f"No location found for address: '{address}'"

        # Return first result
        place = results[0]
        name = place.get("name", "Unknown")
        formatted_address = ", ".join(place.get("formattedAddressLines", []))

        # Extract coordinates
        coordinate = place.get("coordinate", {})
        lat = coordinate.get("latitude")
        lon = coordinate.get("longitude")

        if lat is not None and lon is not None:
            return (
                f"Location: {name}\n"
                f"Address: {formatted_address}\n"
                f"Coordinates: {lat}, {lon}\n"
                f"Google Maps: https://maps.google.com/?q={lat},{lon}"
            )
        else:
            return f"Location: {name}\nAddress: {formatted_address}\n(Coordinates not available)"

    except RuntimeError as e:
        return f"Authentication error: {str(e)}"
    except requests.exceptions.Timeout:
        return "Error: Request to Apple Maps API timed out"
    except requests.exceptions.RequestException as e:
        return f"Error calling Apple Maps API: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


# Main entry point
if __name__ == "__main__":
    # Run the MCP server
    # For Cloud Run, we just run normally and FastMCP handles everything
    # The PORT environment variable is automatically detected
    mcp.run()
