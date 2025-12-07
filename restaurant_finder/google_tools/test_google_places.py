#!/usr/bin/env python3
"""
Test script for Google Places MCP Server

This script tests all the Google Places MCP tools to verify they work correctly.
Run this locally to test the MCP server before deploying to Cloud Run.

Usage:
    # Make sure you have GOOGLE_MAPS_API_KEY in your .env file
    python test_google_places.py
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the MCP tools directly from the local file
from google_places_mcp import (
    search_places,
    get_place_details,
    search_nearby,
    autocomplete_places,
    geocode_address
)


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_result(result):
    """Print a result with formatting."""
    print("\n" + result)
    print("-" * 80)


def test_search_places():
    """Test the search_places tool."""
    print_section("TEST 1: Search Places - Thai Restaurants in San Francisco")

    result = search_places(
        query="Thai restaurants in San Francisco",
        limit=3
    )
    print_result(result)


def test_search_places_with_location():
    """Test search_places with location parameter."""
    print_section("TEST 2: Search Places with Location - Coffee shops near Times Square")

    result = search_places(
        query="coffee shops",
        location="Times Square, New York",
        radius_meters=1000,
        limit=3
    )
    print_result(result)


def test_geocode_address():
    """Test the geocode_address tool."""
    print_section("TEST 3: Geocode Address - Google Headquarters")

    result = geocode_address(
        address="1600 Amphitheatre Parkway, Mountain View, CA"
    )
    print_result(result)

    # Return coordinates for use in next test
    if "Coordinates:" in result:
        coords_line = [line for line in result.split('\n') if "Coordinates:" in line][0]
        coords = coords_line.split("Coordinates:")[1].strip()
        lat, lon = coords.split(",")
        return float(lat.strip()), float(lon.strip())
    return None


def test_geocode_san_diego_convention_center():
    """Test geocoding the San Diego Convention Center."""
    print_section("TEST 3b: Geocode Address - San Diego Convention Center")

    result = geocode_address(
        address="San Diego Convention Center"
    )
    print_result(result)

    # Return coordinates for potential use
    if "Coordinates:" in result:
        coords_line = [line for line in result.split('\n') if "Coordinates:" in line][0]
        coords = coords_line.split("Coordinates:")[1].strip()
        lat, lon = coords.split(",")
        return float(lat.strip()), float(lon.strip())
    return None


def test_search_nearby(lat=37.7749, lon=-122.4194):
    """Test the search_nearby tool."""
    print_section(f"TEST 4: Search Nearby - Restaurants near ({lat}, {lon})")

    result = search_nearby(
        latitude=lat,
        longitude=lon,
        place_type="restaurant",
        keyword="italian",
        radius_meters=2000,
        limit=3
    )
    print_result(result)


def test_autocomplete():
    """Test the autocomplete_places tool."""
    print_section("TEST 5: Autocomplete - 'Golden Gate'")

    result = autocomplete_places(
        input_text="Golden Gate",
        location="San Francisco, CA"
    )
    print_result(result)

    # Extract a place ID if available for next test
    if "Place ID:" in result:
        lines = result.split('\n')
        for line in lines:
            if "Place ID:" in line:
                place_id = line.split("Place ID:")[1].strip()
                return place_id
    return None


def test_get_place_details(place_id=None):
    """Test the get_place_details tool."""
    if not place_id:
        # Use a known Place ID for Golden Gate Bridge
        place_id = "ChIJw____96GhYARCVVwg5cT7c0"
        print_section(f"TEST 6: Get Place Details - Golden Gate Bridge (using known Place ID)")
    else:
        print_section(f"TEST 6: Get Place Details - Place ID: {place_id}")

    result = get_place_details(place_id=place_id)
    print_result(result)


def test_error_handling():
    """Test error handling with invalid inputs."""
    print_section("TEST 7: Error Handling - Empty Query")

    result = search_places(query="")
    print_result(result)

    print_section("TEST 8: Error Handling - Invalid Place ID")

    result = get_place_details(place_id="invalid_place_id_12345")
    print_result(result)


def main():
    """Run all tests."""
    # Check API key is configured
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        print("❌ ERROR: GOOGLE_MAPS_API_KEY not found in environment variables")
        print("\nPlease set your Google Maps API key in .env file:")
        print("  GOOGLE_MAPS_API_KEY=your_api_key_here")
        sys.exit(1)

    print("\n" + "🚀 Google Places MCP Server Test Suite".center(80))
    print("=" * 80)
    print(f"API Key: {api_key[:8]}...{api_key[-4:]}")
    print("=" * 80)

    try:
        # Run all tests
        test_search_places()
        test_search_places_with_location()

        coords = test_geocode_address()

        # Test San Diego Convention Center geocoding
        sd_coords = test_geocode_san_diego_convention_center()

        if coords:
            test_search_nearby(coords[0], coords[1])
        else:
            test_search_nearby()  # Use default coordinates

        place_id = test_autocomplete()
        test_get_place_details(place_id)

        test_error_handling()

        # Summary
        print_section("✅ All Tests Completed Successfully!")
        print("\nThe Google Places MCP server is working correctly.")
        print("\nNext steps:")
        print("  1. Deploy to Cloud Run: cd google_tools && ./deploy.sh")
        print("  2. Use in your agent with get_google_places_toolset()")
        print("=" * 80 + "\n")

    except Exception as e:
        print(f"\n❌ ERROR: Test failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
