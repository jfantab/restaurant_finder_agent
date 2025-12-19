#!/usr/bin/env python3
"""
Script to restructure restaurant addresses CSV from:
    "840 El Paseo de Saratoga, San Jose, CA 95130"
To:
    1,840 El Paseo de Saratoga,San Jose,CA,95130
"""

import re


def parse_address(address_str):
    """
    Parse an address string like "840 El Paseo de Saratoga, San Jose, CA 95130"
    into components: (street, city, state, zip)
    """
    # Pattern: street, city, STATE ZIP
    # State is 2 uppercase letters, ZIP is 5 digits (optionally with -4 more)
    pattern = r'^(.+),\s*(.+),\s*([A-Z]{2})\s+(\d{5}(?:-\d{4})?)$'
    match = re.match(pattern, address_str.strip())

    if match:
        street = match.group(1).strip()
        city = match.group(2).strip()
        state = match.group(3).strip()
        zipcode = match.group(4).strip()
        return street, city, state, zipcode
    else:
        # If parsing fails, return None to skip the line
        print(f"Warning: Could not parse address: {address_str}")
        return None


def restructure_csv(input_file, output_file):
    """Read the input CSV and write restructured output."""
    # Read file with universal newline support
    with open(input_file, 'r', encoding='utf-8', newline='') as infile:
        lines = infile.read().replace('\r\n', '\n').replace('\r', '\n').split('\n')

    # Skip header row
    lines = lines[1:]

    rows = []
    idx = 1
    for line in lines:
        line = line.strip()
        if not line:
            continue

        result = parse_address(line)
        if result:
            street, city, state, zipcode = result
            rows.append(f'{idx},{street},{city},{state},{zipcode}')
            idx += 1

    with open(output_file, 'w', encoding='utf-8') as outfile:
        outfile.write('\n'.join(rows))

    print(f"Processed {len(rows)} addresses")
    print(f"Output written to: {output_file}")


if __name__ == "__main__":
    input_file = "sj-restaurants-addresses.csv"
    output_file = "sj-restaurants-addresses-restructured.csv"

    restructure_csv(input_file, output_file)
