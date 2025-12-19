#!/usr/bin/env python3
"""
SQL Restaurant Database MCP Server

This MCP server exposes SQL-based restaurant search functionality as tools that can be
used by AI agents through the Model Context Protocol.

Features:
- Restaurant search by location (Haversine distance)
- Restaurant reviews retrieval
- Clean result formatting optimized for LLM consumption
- Error handling with informative messages

Run as MCP server:
    python sql_mcp.py

Environment variables required:
- NEON_DATABASE_URL: Your Neon PostgreSQL connection string
"""

import os
from typing import Optional
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Load environment variables
load_dotenv()

# Initialize the MCP Server
mcp = FastMCP("SQLRestaurants")

# Lazy database connection (initialized on first use)
_db_connection = None


def get_db():
    """Get or create the database connection."""
    global _db_connection
    if _db_connection is None:
        from db_connection import get_db_connection
        _db_connection = get_db_connection()
    return _db_connection


@mcp.tool()
def search_restaurants(
    latitude: float,
    longitude: float,
    radius_miles: float = 5.0,
    cuisine: Optional[str] = None,
    min_rating: Optional[float] = None,
    keywords: Optional[str] = None,
    limit: int = 10
) -> str:
    """
    Search for restaurants within a radius of a location.

    Uses Haversine formula to calculate distance from the given coordinates.

    Args:
        latitude: Latitude of the search center point
        longitude: Longitude of the search center point
        radius_miles: Search radius in miles (default: 5.0)
        cuisine: Optional cuisine type or category to filter by (e.g., "Italian", "Thai", "Pizza")
        min_rating: Optional minimum rating filter (1.0-5.0)
        keywords: Optional keywords to search in restaurant name and categories (e.g., "sushi", "burger")
        limit: Maximum number of results to return (default: 10, max: 50)

    Returns:
        Formatted string with restaurant search results including name, address,
        rating, distance, and categories
    """
    try:
        db = get_db()

        # Haversine formula in SQL to calculate distance in miles
        # 3959 is Earth's radius in miles
        haversine_sql = f"""
            3959 * acos(
                cos(radians({latitude})) * cos(radians(latitude)) *
                cos(radians(longitude) - radians({longitude})) +
                sin(radians({latitude})) * sin(radians(latitude))
            )
        """

        # Build WHERE clauses
        where_clauses = [
            "latitude IS NOT NULL",
            "longitude IS NOT NULL",
            f"({haversine_sql}) <= {radius_miles}"
        ]

        params = []

        if cuisine:
            where_clauses.append("LOWER(main_category) LIKE %s")
            cuisine_pattern = f"%{cuisine.lower()}%"
            params.append(cuisine_pattern)

        if keywords:
            where_clauses.append("(LOWER(name) LIKE %s OR LOWER(categories) LIKE %s)")
            keywords_pattern = f"%{keywords.lower()}%"
            params.append(keywords_pattern)
            params.append(keywords_pattern)

        if min_rating is not None:
            where_clauses.append("rating >= %s")
            params.append(min_rating)

        # Clamp limit
        limit = min(max(1, limit), 10)

        query = f"""
            SELECT
                place_id,
                name,
                address,
                rating,
                reviews as review_count,
                main_category,
                categories,
                phone,
                website,
                workday_timing as hours,
                latitude,
                longitude,
                {haversine_sql} as distance_miles
            FROM restaurants.sj_restaurants
            WHERE {' AND '.join(where_clauses)}
            ORDER BY distance_miles ASC
            LIMIT {limit}
        """

        results = db.execute_query(query, tuple(params) if params else None)

        if not results:
            return f"No restaurants found within {radius_miles} miles of the specified location."

        # Format results for LLM consumption
        output_lines = [f"Found {len(results)} restaurants within {radius_miles} miles:\n"]

        for i, r in enumerate(results, 1):
            distance = r.get("distance_miles", 0)
            rating = r.get("rating")
            rating_str = f"Rating: {rating}/5" if rating else "No rating"
            review_count = r.get("review_count", 0)

            output_lines.append(f"**{i}. {r['name']}**")
            output_lines.append(f"   Address: {r.get('address', 'Address not available')}")
            output_lines.append(f"   Distance: {distance:.1f} miles away")
            output_lines.append(f"   {rating_str} ({review_count} reviews)")

            if r.get("main_category"):
                output_lines.append(f"   Category: {r['main_category']}")

            if r.get("phone"):
                output_lines.append(f"   Phone: {r['phone']}")

            if r.get("website"):
                output_lines.append(f"   Website: {r['website']}")

            output_lines.append(f"   Place ID: {r.get('place_id', 'N/A')}")
            output_lines.append(f"   Latitude: {r.get('latitude')}")
            output_lines.append(f"   Longitude: {r.get('longitude')}")
            output_lines.append("")

        return "\n".join(output_lines)

    except Exception as e:
        return f"Error searching restaurants: {str(e)}"


@mcp.tool()
def get_restaurant_reviews(
    place_id: str,
    limit: int = 10
) -> str:
    """
    Get reviews for a specific restaurant by its place_id.

    Args:
        place_id: The Google Place ID of the restaurant
        limit: Maximum number of reviews to return (default: 10, max: 20)

    Returns:
        Formatted string with reviews including reviewer name, rating,
        review text, and date
    """
    try:
        db = get_db()

        # Clamp limit
        limit = min(max(1, limit), 20)

        # Get reviews
        query = """
            SELECT
                name as reviewer_name,
                rating,
                review_text,
                published_at_date,
                is_local_guide,
                total_number_of_reviews_by_reviewer,
                response_from_owner_text
            FROM restaurants.sj_reviews
            WHERE place_id = %s
            ORDER BY published_at_date DESC
            LIMIT %s
        """

        results = db.execute_query(query, (place_id, limit))

        if not results:
            return f"No reviews found for restaurant with place_id: {place_id}"

        # Format results
        output_lines = [f"Reviews for restaurant **{place_id}** ({len(results)} reviews):\n"]

        for i, r in enumerate(results, 1):
            reviewer = r.get("reviewer_name", "Anonymous")
            rating = r.get("rating", "N/A")
            review_text = r.get("review_text", "No review text")
            date = r.get("published_at_date", "Unknown date")
            is_local_guide = r.get("is_local_guide", "").lower() == "true"

            output_lines.append(f"**Review {i}**")
            output_lines.append(f"   Reviewer: {reviewer}" + (" (Local Guide)" if is_local_guide else ""))
            output_lines.append(f"   Rating: {rating}/5")
            output_lines.append(f"   Date: {date}")
            output_lines.append(f"   Review: {review_text}")

            if r.get("response_from_owner_text"):
                owner_response = r["response_from_owner_text"]
                output_lines.append(f"   Owner response: {owner_response[:200]}{'...' if len(str(owner_response)) > 200 else ''}")

            output_lines.append("")

        return "\n".join(output_lines)

    except Exception as e:
        return f"Error fetching reviews: {str(e)}"


@mcp.tool()
def get_restaurant_details(place_id: str) -> str:
    """
    Get detailed information about a specific restaurant by its place_id.

    Args:
        place_id: The Google Place ID of the restaurant

    Returns:
        Formatted string with restaurant details including name, address,
        rating, phone, website, hours, and coordinates
    """
    try:
        db = get_db()

        query = """
            SELECT
                place_id,
                name,
                address,
                rating,
                reviews as review_count,
                main_category,
                categories,
                phone,
                website,
                workday_timing as hours,
                latitude,
                longitude
            FROM restaurants.sj_restaurants
            WHERE place_id = %s
        """

        results = db.execute_query(query, (place_id,))

        if not results:
            return f"No restaurant found with place_id: {place_id}"

        r = results[0]

        output_lines = [f"**{r['name']}**\n"]
        output_lines.append(f"Address: {r.get('address', 'Address not available')}")

        if r.get("rating"):
            review_count = r.get("review_count", 0)
            output_lines.append(f"Rating: {r['rating']}/5 ({review_count} reviews)")

        if r.get("main_category"):
            output_lines.append(f"Category: {r['main_category']}")

        if r.get("categories"):
            output_lines.append(f"All Categories: {r['categories']}")

        if r.get("phone"):
            output_lines.append(f"Phone: {r['phone']}")

        if r.get("website"):
            output_lines.append(f"Website: {r['website']}")

        if r.get("hours"):
            output_lines.append(f"Hours: {r['hours']}")

        output_lines.append(f"\nPlace ID: {r.get('place_id', 'N/A')}")
        output_lines.append(f"Latitude: {r.get('latitude')}")
        output_lines.append(f"Longitude: {r.get('longitude')}")

        return "\n".join(output_lines)

    except Exception as e:
        return f"Error fetching restaurant details: {str(e)}"


# Main entry point
if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
