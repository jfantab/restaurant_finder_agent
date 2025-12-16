#!/usr/bin/env python3
"""
Test script to fetch place reviews from Google Places API.

This script searches for a place by query/location, then retrieves
detailed reviews for that place and outputs them to a formatted markdown file.

Usage:
    # Make sure you have GOOGLE_PLACES_API_KEY in your .env file
    python test_place_reviews.py
    python test_place_reviews.py "Tartine Bakery" "San Francisco"
    python test_place_reviews.py "coffee shops" "New York, NY"

Output:
    Creates a markdown file: reviews_<place_name>.md
"""

import os
import sys
import json
import re
import requests
from datetime import datetime
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
BASE_URL = "https://places.googleapis.com/v1"


def make_request(
    endpoint: str,
    method: str = "GET",
    json_data: Optional[Dict[str, Any]] = None,
    field_mask: str = "*"
) -> Dict[str, Any]:
    """Make a request to the Google Places API."""
    if not API_KEY:
        raise RuntimeError("GOOGLE_MAPS_API_KEY must be set in environment variables")

    url = f"{BASE_URL}/{endpoint}"
    headers = {
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": field_mask
    }

    if method == "POST":
        resp = requests.post(url, headers=headers, json=json_data, timeout=10)
    else:
        resp = requests.get(url, headers=headers, timeout=10)

    resp.raise_for_status()
    return resp.json()


def search_place(query: str, location: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Search for a place and return the first result.

    Args:
        query: Search query (e.g., "Tartine Bakery")
        location: Optional location context (e.g., "San Francisco")

    Returns:
        Place data dictionary or None if not found
    """
    search_query = f"{query} in {location}" if location else query

    request_body = {
        "textQuery": search_query,
        "pageSize": 1
    }

    data = make_request(
        "places:searchText",
        method="POST",
        json_data=request_body
    )

    places = data.get("places", [])
    return places[0] if places else None


def get_place_reviews(place_id: str) -> Dict[str, Any]:
    """
    Get detailed place information including reviews.

    Args:
        place_id: Google Place ID

    Returns:
        Place data with reviews
    """
    # Request specific fields including reviews
    field_mask = ",".join([
        "id",
        "displayName",
        "formattedAddress",
        "rating",
        "userRatingCount",
        "reviews"
    ])

    return make_request(
        f"places/{place_id}",
        field_mask=field_mask
    )


def format_review(review: Dict[str, Any], index: int) -> str:
    """Format a single review for console display."""
    author = review.get("authorAttribution", {})
    author_name = author.get("displayName", "Anonymous")
    author_uri = author.get("uri", "")

    rating = review.get("rating", "N/A")

    # Review text
    text_data = review.get("text", {})
    review_text = text_data.get("text", "No review text")
    language = text_data.get("languageCode", "unknown")

    # Time info
    publish_time = review.get("publishTime", "")
    relative_time = review.get("relativePublishTimeDescription", "")

    lines = [
        f"{'=' * 60}",
        f"Review #{index}",
        f"{'=' * 60}",
        f"Author: {author_name}",
    ]

    if author_uri:
        lines.append(f"Profile: {author_uri}")

    lines.extend([
        f"Rating: {'⭐' * int(rating) if isinstance(rating, (int, float)) else rating}",
        f"Posted: {relative_time} ({publish_time})",
        f"Language: {language}",
        f"",
        f"Review:",
        f"{review_text}",
    ])

    return "\n".join(lines)


def format_review_markdown(review: Dict[str, Any], index: int) -> str:
    """Format a single review as markdown."""
    author = review.get("authorAttribution", {})
    author_name = author.get("displayName", "Anonymous")
    author_uri = author.get("uri", "")

    rating = review.get("rating", 0)

    # Review text
    text_data = review.get("text", {})
    review_text = text_data.get("text", "No review text")

    # Time info
    relative_time = review.get("relativePublishTimeDescription", "Unknown date")

    # Build star rating display
    stars = "⭐" * int(rating) if isinstance(rating, (int, float)) else str(rating)

    # Author with optional link
    if author_uri:
        author_display = f"[{author_name}]({author_uri})"
    else:
        author_display = author_name

    lines = [
        f"### Review {index}",
        f"",
        f"**Rating:** {stars} ({rating}/5)",
        f"",
        f"**Author:** {author_display}",
        f"",
        f"**Posted:** {relative_time}",
        f"",
        f"> {review_text}",
        f"",
        f"---",
        f"",
    ]

    return "\n".join(lines)


def generate_markdown_report(
    place_name: str,
    place_address: str,
    place_id: str,
    rating: float,
    review_count: int,
    reviews: List[Dict[str, Any]],
    query: str,
    location: Optional[str]
) -> str:
    """Generate a complete markdown report for the place reviews."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        f"# {place_name} - Reviews",
        f"",
        f"*Generated: {timestamp}*",
        f"",
        f"## Place Information",
        f"",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| **Name** | {place_name} |",
        f"| **Address** | {place_address} |",
        f"| **Overall Rating** | {'⭐' * int(rating) if rating else 'N/A'} ({rating}/5) |",
        f"| **Total Reviews** | {review_count} |",
        f"| **Place ID** | `{place_id}` |",
        f"",
        f"## Search Query",
        f"",
        f"- **Query:** {query}",
        f"- **Location:** {location or 'Not specified'}",
        f"",
        f"---",
        f"",
        f"## Reviews ({len(reviews)} fetched)",
        f"",
    ]

    if not reviews:
        lines.append("*No reviews available for this place.*")
    else:
        for i, review in enumerate(reviews, 1):
            lines.append(format_review_markdown(review, i))

    # Add raw JSON section at the end
    lines.extend([
        f"## Raw Data (JSON)",
        f"",
        f"<details>",
        f"<summary>Click to expand raw review data</summary>",
        f"",
        f"```json",
        json.dumps(reviews, indent=2, ensure_ascii=False),
        f"```",
        f"",
        f"</details>",
    ])

    return "\n".join(lines)


def sanitize_filename(name: str) -> str:
    """Sanitize a string to be used as a filename."""
    # Replace spaces with underscores, remove special chars
    sanitized = re.sub(r'[^\w\s-]', '', name)
    sanitized = re.sub(r'[\s]+', '_', sanitized)
    return sanitized.lower()[:50]


def main():
    # Parse command line arguments
    if len(sys.argv) >= 2:
        query = sys.argv[1]
        location = sys.argv[2] if len(sys.argv) >= 3 else None
    else:
        # Default test query
        query = "Tartine Bakery"
        location = "San Francisco"

    # Check API key
    if not API_KEY:
        print("ERROR: GOOGLE_MAPS_API_KEY not found in environment")
        print("Please set your API key in .env file:")
        print("  GOOGLE_MAPS_API_KEY=your_api_key_here")
        sys.exit(1)

    print(f"\n{'#' * 60}")
    print("Google Places Reviews Test")
    print(f"{'#' * 60}")
    print(f"API Key: {API_KEY[:8]}...{API_KEY[-4:]}")
    print(f"Query: {query}")
    print(f"Location: {location or 'Not specified'}")
    print(f"{'#' * 60}\n")

    try:
        # Step 1: Search for the place
        print("Step 1: Searching for place...")
        place = search_place(query, location)

        if not place:
            print(f"No place found for query: {query}")
            sys.exit(1)

        place_id = place.get("id")
        place_name = place.get("displayName", {}).get("text", "Unknown")
        place_address = place.get("formattedAddress", "No address")

        print(f"Found: {place_name}")
        print(f"Address: {place_address}")
        print(f"Place ID: {place_id}")

        # Step 2: Get reviews
        print("\nStep 2: Fetching reviews...")
        details = get_place_reviews(place_id)

        rating = details.get("rating", "N/A")
        review_count = details.get("userRatingCount", 0)
        reviews = details.get("reviews", [])

        print(f"\nOverall Rating: {rating} ({review_count} reviews)")
        print(f"Reviews fetched: {len(reviews)}")

        # Step 3: Display reviews to console
        print(f"\n{'#' * 60}")
        print("REVIEWS")
        print(f"{'#' * 60}")

        if not reviews:
            print("\nNo reviews available for this place.")
        else:
            for i, review in enumerate(reviews, 1):
                print(f"\n{format_review(review, i)}")

        # Step 4: Generate and save markdown file
        print(f"\n{'#' * 60}")
        print("GENERATING MARKDOWN REPORT")
        print(f"{'#' * 60}")

        markdown_content = generate_markdown_report(
            place_name=place_name,
            place_address=place_address,
            place_id=place_id,
            rating=rating,
            review_count=review_count,
            reviews=reviews,
            query=query,
            location=location
        )

        # Create output filename
        output_filename = f"reviews_{sanitize_filename(place_name)}.md"
        output_path = os.path.join(os.path.dirname(__file__), output_filename)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        print(f"\nMarkdown report saved to: {output_path}")
        print(f"Filename: {output_filename}")

        print(f"\n{'#' * 60}")
        print("Test completed successfully!")
        print(f"{'#' * 60}\n")

    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}")
        try:
            error_detail = e.response.json()
            print(f"Details: {json.dumps(error_detail, indent=2)}")
        except:
            pass
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
