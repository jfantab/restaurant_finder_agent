#!/usr/bin/env python3
"""
Test script for Google Places Cloud Run MCP Server

This script tests the Google Places MCP server deployed on Cloud Run
by calling the function tools that make HTTP requests to the deployed endpoints.

Usage:
    # Make sure GOOGLE_PLACES_MCP_URL is set in your .env file
    python test_google_places_cloud.py
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the function tools that call Cloud Run
from google_places_function_tool import (
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
    """Test the search_places tool via Cloud Run."""
    print_section("TEST 1: Search Places - Thai Restaurants in San Francisco")

    result = search_places(
        query="Thai restaurants in San Francisco",
        limit=3
    )
    print_result(result)
    return "Error" not in result


def test_search_places_with_location():
    """Test search_places with location parameter via Cloud Run."""
    print_section("TEST 2: Search Places with Location - Coffee shops near Times Square")

    result = search_places(
        query="coffee shops",
        location="Times Square, New York",
        radius_meters=1000,
        limit=3
    )
    print_result(result)
    return "Error" not in result


def test_geocode_address():
    """Test the geocode_address tool via Cloud Run."""
    print_section("TEST 3: Geocode Address - Google Headquarters")

    result = geocode_address(
        address="1600 Amphitheatre Parkway, Mountain View, CA"
    )
    print_result(result)

    # Return coordinates for use in next test
    if "Coordinates:" in result and "Error" not in result:
        coords_line = [line for line in result.split('\n') if "Coordinates:" in line][0]
        coords = coords_line.split("Coordinates:")[1].strip()
        lat, lon = coords.split(",")
        return float(lat.strip()), float(lon.strip())
    return None


def test_geocode_san_diego():
    """Test geocoding San Diego Convention Center via Cloud Run."""
    print_section("TEST 3b: Geocode Address - 111 Harbor Dr, San Diego, CA 92101")

    result = geocode_address(
        address="111 Harbor Dr, San Diego, CA 92101"
    )
    print_result(result)

    # Return coordinates for potential use
    if "Coordinates:" in result and "Error" not in result:
        coords_line = [line for line in result.split('\n') if "Coordinates:" in line][0]
        coords = coords_line.split("Coordinates:")[1].strip()
        lat, lon = coords.split(",")
        return float(lat.strip()), float(lon.strip())
    return None


def test_search_nearby(lat=37.7749, lon=-122.4194):
    """Test the search_nearby tool via Cloud Run."""
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
    return "Error" not in result


def test_autocomplete():
    """Test the autocomplete_places tool via Cloud Run."""
    print_section("TEST 5: Autocomplete - 'Golden Gate'")

    result = autocomplete_places(
        input_text="Golden Gate",
        location="San Francisco, CA"
    )
    print_result(result)

    # Extract a place ID if available for next test
    if "Place ID:" in result and "Error" not in result:
        lines = result.split('\n')
        for line in lines:
            if "Place ID:" in line:
                place_id = line.split("Place ID:")[1].strip()
                return place_id
    return None


def test_get_place_details(place_id=None):
    """Test the get_place_details tool via Cloud Run."""
    if not place_id:
        # Use a known Place ID for Golden Gate Bridge
        place_id = "ChIJw____96GhYARCVVwg5cT7c0"
        print_section(f"TEST 6: Get Place Details - Golden Gate Bridge (using known Place ID)")
    else:
        print_section(f"TEST 6: Get Place Details - Place ID: {place_id}")

    result = get_place_details(place_id=place_id)
    print_result(result)
    return "Error" not in result


def test_error_handling():
    """Test error handling with invalid inputs via Cloud Run."""
    print_section("TEST 7: Error Handling - Empty Query")

    result = search_places(query="")
    print_result(result)

    print_section("TEST 8: Error Handling - Invalid Place ID")

    result = get_place_details(place_id="invalid_place_id_12345")
    print_result(result)


def main():
    """Run all tests."""
    # Check Cloud Run URL is configured
    mcp_url = os.getenv("GOOGLE_PLACES_MCP_URL")
    if not mcp_url:
        print("❌ ERROR: GOOGLE_PLACES_MCP_URL not found in environment variables")
        print("\nPlease set your Google Places MCP Cloud Run URL in .env file:")
        print("  GOOGLE_PLACES_MCP_URL=https://google-places-mcp-xxxxx-uw.a.run.app/sse")
        sys.exit(1)

    print("\n" + "🚀 Google Places Cloud Run MCP Server Test Suite".center(80))
    print("=" * 80)
    print(f"Cloud Run URL: {mcp_url}")
    print("=" * 80)

    passed_tests = 0
    total_tests = 0

    try:
        # Run all tests
        total_tests += 1
        if test_search_places():
            passed_tests += 1

        total_tests += 1
        if test_search_places_with_location():
            passed_tests += 1

        coords = test_geocode_address()
        total_tests += 1
        if coords:
            passed_tests += 1

        # Test San Diego geocoding
        sd_coords = test_geocode_san_diego()
        total_tests += 1
        if sd_coords:
            passed_tests += 1

        if coords:
            total_tests += 1
            if test_search_nearby(coords[0], coords[1]):
                passed_tests += 1
        else:
            total_tests += 1
            if test_search_nearby():  # Use default coordinates
                passed_tests += 1

        place_id = test_autocomplete()
        total_tests += 1
        if place_id:
            passed_tests += 1

        total_tests += 1
        if test_get_place_details(place_id):
            passed_tests += 1

        test_error_handling()

        # Summary
        print_section(f"Test Results: {passed_tests}/{total_tests} tests passed")

        if passed_tests == total_tests:
            print("\n✅ All Tests Completed Successfully!")
            print("\nThe Google Places Cloud Run MCP server is working correctly.")
        else:
            print(f"\n⚠️  {total_tests - passed_tests} test(s) failed.")
            print("\nThe Cloud Run server may have issues. Check:")
            print("  1. Server is deployed and running")
            print("  2. GOOGLE_MAPS_API_KEY is set in Cloud Run environment")
            print("  3. Server logs for errors: gcloud run logs read google-places-mcp")

        print("=" * 80 + "\n")

    except Exception as e:
        print(f"\n❌ ERROR: Test failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
