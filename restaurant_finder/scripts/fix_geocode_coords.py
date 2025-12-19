#!/usr/bin/env python3
"""
Script to swap lat/long coordinates in GeocodeResults.csv
From: "-121.911805615845,37.349495936454" (long,lat)
To: "37.349495936454,-121.911805615845" (lat,long)
"""

import csv


def swap_coordinates(coord_str):
    """Swap long,lat to lat,long."""
    if not coord_str or ',' not in coord_str:
        return coord_str
    parts = coord_str.split(',')
    if len(parts) == 2:
        return f"{parts[1]},{parts[0]}"
    return coord_str


def fix_geocode_csv(input_file, output_file):
    """Read the geocode CSV and swap coordinates."""
    rows = []

    with open(input_file, 'r', encoding='utf-8') as infile:
        reader = csv.reader(infile)
        for row in reader:
            # Column 5 (0-indexed) contains the coordinates for matched addresses
            # Some rows have "No_Match" and fewer columns
            if len(row) >= 6 and row[2] == "Match":
                row[5] = swap_coordinates(row[5])
            rows.append(row)

    with open(output_file, 'w', encoding='utf-8', newline='') as outfile:
        writer = csv.writer(outfile)
        writer.writerows(rows)

    print(f"Processed {len(rows)} rows")
    print(f"Output written to: {output_file}")


if __name__ == "__main__":
    input_file = "GeocodeResults.csv"
    output_file = "GeocodeResults_fixed.csv"

    fix_geocode_csv(input_file, output_file)
