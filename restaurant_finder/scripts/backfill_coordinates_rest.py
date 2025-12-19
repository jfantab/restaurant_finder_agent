#!/usr/bin/env python3
"""Backfill latitude/longitude coordinates for restaurants using Google Places API.

Uses REST API with requests instead of the google-maps-places SDK.
"""

import os
import sys
import time
from typing import Optional, Tuple

import requests
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sql_tools.db_connection import get_db_connection

load_dotenv()


def get_lat_lng_from_place_id(
    api_key: str,
    place_id: str
) -> Tuple[Optional[float], Optional[float]]:
    """Fetch latitude/longitude for a place_id using Google Places API.

    Args:
        api_key: Google Maps API key
        place_id: Google Place ID

    Returns:
        Tuple of (latitude, longitude) or (None, None) if failed
    """
    url = f"https://places.googleapis.com/v1/places/{place_id}"

    headers = {
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "location"
    }

    try:
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            if "location" in data:
                return data["location"]["latitude"], data["location"]["longitude"]
        else:
            print(f"  API error {response.status_code}: {response.text[:100]}")

        return None, None

    except Exception as e:
        print(f"  Error fetching place {place_id}: {e}")
        return None, None


def backfill_coordinates(
    batch_size: int = 100,
    delay_seconds: float = 0.1,
    dry_run: bool = False
) -> dict:
    """Backfill lat/lng coordinates for all restaurants missing them.

    Args:
        batch_size: Number of restaurants to process before committing
        delay_seconds: Delay between API calls to avoid rate limiting
        dry_run: If True, don't actually update the database

    Returns:
        Dict with statistics: total, updated, failed, skipped
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_MAPS_API_KEY environment variable not set")

    db = get_db_connection()

    # Get all restaurants missing coordinates
    query = """
        SELECT place_id, name
        FROM restaurants.sj_restaurants
        WHERE (latitude IS NULL OR longitude IS NULL)
        AND place_id IS NOT NULL
    """
    restaurants = db.execute_query(query)

    stats = {
        "total": len(restaurants),
        "updated": 0,
        "failed": 0,
        "skipped": 0
    }

    print(f"Found {stats['total']} restaurants missing coordinates")

    for i, restaurant in enumerate(restaurants):
        place_id = restaurant["place_id"]
        name = restaurant["name"]

        if not place_id:
            stats["skipped"] += 1
            continue

        lat, lng = get_lat_lng_from_place_id(api_key, place_id)

        if lat is not None and lng is not None:
            if not dry_run:
                update_query = """
                    UPDATE restaurants.sj_restaurants
                    SET latitude = %s, longitude = %s
                    WHERE place_id = %s
                """
                db.execute_write(update_query, (lat, lng, place_id))

            stats["updated"] += 1
            print(f"[{i+1}/{stats['total']}] Updated: {name} ({lat}, {lng})")
        else:
            stats["failed"] += 1
            print(f"[{i+1}/{stats['total']}] Failed: {name} (place_id: {place_id})")

        # Rate limiting
        time.sleep(delay_seconds)

        # Progress update every batch
        if (i + 1) % batch_size == 0:
            print(f"\n--- Progress: {i+1}/{stats['total']} processed ---")
            print(f"    Updated: {stats['updated']}, Failed: {stats['failed']}, Skipped: {stats['skipped']}\n")

    print("\n=== Backfill Complete ===")
    print(f"Total: {stats['total']}")
    print(f"Updated: {stats['updated']}")
    print(f"Failed: {stats['failed']}")
    print(f"Skipped: {stats['skipped']}")

    return stats


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Backfill restaurant coordinates")
    parser.add_argument("--dry-run", action="store_true", help="Don't update database")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size for progress updates")
    parser.add_argument("--delay", type=float, default=0.1, help="Delay between API calls (seconds)")

    args = parser.parse_args()

    backfill_coordinates(
        batch_size=args.batch_size,
        delay_seconds=args.delay,
        dry_run=args.dry_run
    )
