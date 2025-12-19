#!/usr/bin/env python3
"""
Upload lat/long coordinates from GeocodeResults_fixed.csv to Neon DB restaurants table.

Matches restaurants by address and updates latitude/longitude columns.
"""

import csv
import os
import sys

from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sql_tools.db_connection import get_db_connection

load_dotenv()


def normalize_address(address: str) -> str:
    """Normalize address for matching by converting to uppercase and removing extra spaces."""
    return ' '.join(address.upper().strip().split())


def parse_geocode_csv(filepath: str) -> list[dict]:
    """Parse the geocode results CSV file.

    Returns list of dicts with keys: id, input_address, lat, lng
    Only returns rows with successful matches.
    """
    results = []

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 3:
                continue

            row_id = row[0].strip('"')
            input_address = row[1].strip('"')
            match_status = row[2].strip('"')

            # Only process matched rows
            if match_status != "Match":
                continue

            if len(row) < 6:
                continue

            coords = row[5].strip('"')
            if ',' not in coords:
                continue

            lat_str, lng_str = coords.split(',')
            try:
                lat = float(lat_str)
                lng = float(lng_str)
            except ValueError:
                print(f"Warning: Invalid coordinates for row {row_id}: {coords}")
                continue

            results.append({
                'id': row_id,
                'input_address': input_address,
                'lat': lat,
                'lng': lng
            })

    return results


def ensure_lat_lng_columns(db) -> None:
    """Add latitude and longitude columns if they don't exist."""
    # Check if columns exist
    check_query = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'restaurants'
        AND table_name = 'sj_restaurants'
        AND column_name IN ('latitude', 'longitude')
    """
    existing = db.execute_query(check_query)
    existing_cols = {r['column_name'] for r in existing}

    if 'latitude' not in existing_cols:
        print("Adding latitude column...")
        db.execute_write("ALTER TABLE restaurants.sj_restaurants ADD COLUMN latitude DOUBLE PRECISION")

    if 'longitude' not in existing_cols:
        print("Adding longitude column...")
        db.execute_write("ALTER TABLE restaurants.sj_restaurants ADD COLUMN longitude DOUBLE PRECISION")


def upload_coordinates(
    csv_path: str,
    batch_size: int = 100,
    dry_run: bool = False
) -> dict:
    """Upload coordinates from geocode CSV to the database.

    Matches restaurants by address (normalized for comparison).

    Args:
        csv_path: Path to GeocodeResults_fixed.csv
        batch_size: Number of updates before printing progress
        dry_run: If True, don't actually update the database

    Returns:
        Dict with statistics
    """
    db = get_db_connection()

    # Ensure lat/lng columns exist
    if not dry_run:
        ensure_lat_lng_columns(db)

    # Parse the CSV
    print(f"Parsing {csv_path}...")
    geocode_results = parse_geocode_csv(csv_path)
    print(f"Found {len(geocode_results)} matched addresses in CSV")

    # Get all restaurants from DB
    print("Fetching restaurants from database...")
    query = """
        SELECT place_id, address
        FROM restaurants.sj_restaurants
    """
    db_restaurants = db.execute_query(query)
    print(f"Found {len(db_restaurants)} restaurants in database")

    # Build a lookup by normalized address
    # Use a dict that maps normalized address -> list of restaurants (in case of duplicates)
    address_to_restaurants = {}
    for r in db_restaurants:
        if r['address']:
            norm_addr = normalize_address(r['address'])
            if norm_addr not in address_to_restaurants:
                address_to_restaurants[norm_addr] = []
            address_to_restaurants[norm_addr].append(r)

    stats = {
        'total_csv': len(geocode_results),
        'matched': 0,
        'updated': 0,
        'already_has_coords': 0,
        'not_found': 0,
        'errors': 0
    }

    print(f"\nProcessing {len(geocode_results)} geocode results...")

    for i, geo in enumerate(geocode_results):
        # Normalize the input address from CSV for matching
        # The CSV format is "949 Ruff Dr, San Jose, CA, 95110"
        norm_input = normalize_address(geo['input_address'])

        # Try to find matching restaurant
        matches = address_to_restaurants.get(norm_input, [])

        if not matches:
            # Try without the extra comma before state (CSV has "San Jose, CA, 95110" but DB might have "San Jose, CA 95110")
            alt_norm = norm_input.replace(', CA, ', ', CA ')
            matches = address_to_restaurants.get(alt_norm, [])

        if not matches:
            stats['not_found'] += 1
            if stats['not_found'] <= 10:  # Only print first 10
                print(f"  Not found: {geo['input_address']}")
            continue

        stats['matched'] += 1

        for restaurant in matches:
            # Skip check for existing coords since we just added columns

            # Update the restaurant
            if not dry_run:
                try:
                    update_query = """
                        UPDATE restaurants.sj_restaurants
                        SET latitude = %s, longitude = %s
                        WHERE place_id = %s
                    """
                    db.execute_write(update_query, (geo['lat'], geo['lng'], restaurant['place_id']))
                    stats['updated'] += 1
                except Exception as e:
                    print(f"  Error updating restaurant {restaurant['place_id']}: {e}")
                    stats['errors'] += 1
            else:
                stats['updated'] += 1
                print(f"  [DRY RUN] Would update: {restaurant['place_id']} -> ({geo['lat']}, {geo['lng']})")

        # Progress update
        if (i + 1) % batch_size == 0:
            print(f"  Progress: {i + 1}/{len(geocode_results)} processed, {stats['updated']} updated")

    print("\n=== Upload Complete ===")
    print(f"Total in CSV: {stats['total_csv']}")
    print(f"Matched in DB: {stats['matched']}")
    print(f"Updated: {stats['updated']}")
    print(f"Already had coords: {stats['already_has_coords']}")
    print(f"Not found in DB: {stats['not_found']}")
    print(f"Errors: {stats['errors']}")

    return stats


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Upload geocode coordinates to Neon DB")
    parser.add_argument(
        "--csv",
        default="../GeocodeResults_fixed.csv",
        help="Path to GeocodeResults_fixed.csv"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually update database"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Progress update frequency"
    )

    args = parser.parse_args()

    # Resolve path relative to script location
    csv_path = args.csv
    if not os.path.isabs(csv_path):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(script_dir, csv_path)

    upload_coordinates(
        csv_path=csv_path,
        batch_size=args.batch_size,
        dry_run=args.dry_run
    )
