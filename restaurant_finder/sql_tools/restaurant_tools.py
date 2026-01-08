"""SQL-based restaurant search tools for the restaurant finder agent.

These FunctionTools query the Neon DB instead of Google Places API.
"""

import os
import json
from typing import Optional

from google.adk.tools import FunctionTool

from .db_connection import get_db_connection
from .menu_tools import scrape_restaurant_menu, get_cached_menu


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
        db = get_db_connection()

        print(f"[DEBUG search_restaurants] Searching with lat={latitude}, lng={longitude}, radius={radius_miles} miles")

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
        db = get_db_connection()

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

        print(len(results))
        print(results)

        for i, r in enumerate(results, 1):
            reviewer = r.get("reviewer_name", "Anonymous")
            rating = r.get("rating", "N/A")
            review_text = r.get("review_text", "No review text")
            date = r.get("published_at_date", "Unknown date")
            is_local_guide = r.get("is_local_guide", "").lower() == "true"

            output_lines.append(f"**Review {i}**")
            output_lines.append(f"   👤 {reviewer}" + (" 🏆 Local Guide" if is_local_guide else ""))
            output_lines.append(f"   ⭐ {rating}/5")
            output_lines.append(f"   📅 {date}")
            output_lines.append(f"   💬 {review_text}")

            if r.get("response_from_owner_text"):
                owner_response = r["response_from_owner_text"]
                output_lines.append(f"   🏪 Owner response: {owner_response[:200]}{'...' if len(str(owner_response)) > 200 else ''}")

            output_lines.append("")

        return "\n".join(output_lines)

    except Exception as e:
        return f"Error fetching reviews: {str(e)}"


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
        db = get_db_connection()

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


def check_operating_hours(
    place_id: str,
    day_of_week: Optional[str] = None
) -> str:
    """
    Check a restaurant's operating hours, optionally for a specific day.

    This tool queries the operating_hours table for detailed day-by-day hours.
    If no detailed hours are available, it falls back to the workday_timing field.

    Args:
        place_id: The Google Place ID of the restaurant
        day_of_week: Optional specific day to check (e.g., "Monday", "Tuesday").
                    If None, returns hours for all days. Case-insensitive.

    Returns:
        Formatted string with operating hours information
    """
    try:
        db = get_db_connection()

        # First try the detailed operating_hours table
        query = """
            SELECT
                place_id,
                restaurant_name,
                day,
                opening_hr,
                closing_hr
            FROM restaurants.operating_hours
            WHERE place_id = %s
        """

        params = [place_id]

        # Filter by specific day if provided
        if day_of_week:
            query += " AND LOWER(day) = LOWER(%s)"
            params.append(day_of_week)

        query += " ORDER BY CASE day WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3 WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6 WHEN 'Sunday' THEN 7 END"

        results = db.execute_query(query, tuple(params))

        # If detailed hours exist, format and return them
        if results:
            restaurant_name = results[0].get('restaurant_name', 'Restaurant')
            output_lines = [f"**Operating Hours for {restaurant_name}**\n"]

            for r in results:
                day = r['day']
                opening = r.get('opening_hr')
                closing = r.get('closing_hr')

                if opening and closing:
                    # Format times nicely (HH:MM:SS -> HH:MM AM/PM)
                    opening_str = opening.strftime('%I:%M %p').lstrip('0')
                    closing_str = closing.strftime('%I:%M %p').lstrip('0')
                    output_lines.append(f"   {day}: {opening_str} - {closing_str}")
                else:
                    output_lines.append(f"   {day}: Closed")

            return "\n".join(output_lines)

        # Fallback to workday_timing from sj_restaurants table
        fallback_query = """
            SELECT name, workday_timing as hours
            FROM restaurants.sj_restaurants
            WHERE place_id = %s
        """
        fallback_results = db.execute_query(fallback_query, (place_id,))

        if fallback_results and fallback_results[0].get('hours'):
            restaurant_name = fallback_results[0].get('name', 'Restaurant')
            hours = fallback_results[0]['hours']
            return f"**Operating Hours for {restaurant_name}**\n\n   {hours}"

        # No hours data available
        return f"No operating hours information available for restaurant {place_id}"

    except Exception as e:
        return f"Error checking operating hours: {str(e)}"


def get_restaurants_with_reviews_batch(
    place_ids: list[str],
    reviews_limit: int = 10
) -> str:
    """
    Get details + reviews for MULTIPLE restaurants in ONE query (batch operation).

    This is 10x faster than calling get_restaurant_details and get_restaurant_reviews
    sequentially for each restaurant because it eliminates network round-trips.

    Args:
        place_ids: List of Google Place IDs to fetch data for
        reviews_limit: Maximum number of reviews per restaurant (default: 10, max: 20)

    Returns:
        JSON string with all restaurant data including reviews
    """
    try:
        print(f"[BATCH QUERY] Fetching {len(place_ids)} restaurants in ONE query (10x faster!)")
        db = get_db_connection()

        if not place_ids:
            return json.dumps({"restaurants": []})

        # Clamp reviews limit
        reviews_limit = min(max(1, reviews_limit), 20)

        # ONE query gets details + reviews for ALL restaurants using LATERAL JOIN
        query = """
            SELECT
                r.place_id, r.name, r.address, r.latitude, r.longitude,
                r.rating, r.reviews as review_count, r.phone, r.website,
                r.workday_timing as hours, r.main_category, r.categories,
                COALESCE(
                    json_agg(
                        json_build_object(
                            'author', rev.name,
                            'rating', rev.rating,
                            'text', rev.review_text,
                            'date', rev.published_at_date,
                            'is_local_guide', rev.is_local_guide
                        ) ORDER BY rev.published_at_date DESC
                    ) FILTER (WHERE rev.place_id IS NOT NULL),
                    '[]'::json
                ) as reviews
            FROM restaurants.sj_restaurants r
            LEFT JOIN LATERAL (
                SELECT * FROM restaurants.sj_reviews
                WHERE place_id = r.place_id
                ORDER BY published_at_date DESC
                LIMIT %s
            ) rev ON true
            WHERE r.place_id = ANY(%s)
            GROUP BY r.place_id, r.name, r.address, r.latitude, r.longitude,
                     r.rating, r.reviews, r.phone, r.website, r.workday_timing,
                     r.main_category, r.categories
        """

        results = db.execute_query(query, (reviews_limit, place_ids))

        if not results:
            return json.dumps({"restaurants": []})

        # Format as structured data for LLM
        output = {"restaurants": []}
        for row in results:
            restaurant_data = {
                "place_id": row["place_id"],
                "name": row["name"],
                "address": row["address"],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "rating": row["rating"],
                "review_count": row["review_count"],
                "phone": row.get("phone"),
                "website": row.get("website"),
                "hours": row.get("hours"),
                "category": row.get("main_category"),
                "categories": row.get("categories"),
                "reviews": row["reviews"] if row["reviews"] else []
            }
            output["restaurants"].append(restaurant_data)

        return json.dumps(output, indent=2)

    except Exception as e:
        return f"Error fetching restaurant data: {str(e)}"


# Create FunctionTool instances
search_restaurants_tool = FunctionTool(search_restaurants)
get_restaurant_reviews_tool = FunctionTool(get_restaurant_reviews)
get_restaurant_details_tool = FunctionTool(get_restaurant_details)
check_operating_hours_tool = FunctionTool(check_operating_hours)
get_restaurants_batch_tool = FunctionTool(get_restaurants_with_reviews_batch)
scrape_menu_tool = FunctionTool(scrape_restaurant_menu)
get_cached_menu_tool = FunctionTool(get_cached_menu)


def get_sql_tools():
    """Returns list of SQL-based FunctionTools for restaurant search.

    Returns:
        List of FunctionTool instances for DB queries
    """
    return [
        search_restaurants_tool,
        get_restaurants_batch_tool,  # Batch tool first for priority
        get_restaurant_reviews_tool,
        get_restaurant_details_tool,
        check_operating_hours_tool,  # Check operating hours for specific restaurants
        get_cached_menu_tool,  # Check cache first (fast)
        scrape_menu_tool,  # Scrape if no cache (slower)
    ]
