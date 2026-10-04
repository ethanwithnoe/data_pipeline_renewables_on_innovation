import pandas as pd
import sys
from pathlib import Path
from collections import Counter, defaultdict
from pyproj import Geod

# Global configuration
MAX_DISTANCE_KM = 50  # Maximum distance in kilometers to consider firms as "nearby"
DISTANCE_BANDS_KM = [1, 3, 5, 10, 20, 50]  # Rows of the per-distance table in the summary (paper's proximity table)
COORDINATE_PRECISION = 0  # Spatial index: coordinates rounded to whole degrees (1-degree buckets)

# Initialize CGCS2000 geoid for China (same as GRS80 ellipsoid)
# CGCS2000 parameters: a=6378137.0 m, 1/f=298.257222101
cgcs2000 = Geod(a=6378137.0, f=1/298.257222101)


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the geodesic distance in kilometers between two points
    on the earth (specified in decimal degrees) using CGCS2000 ellipsoid.
    """
    try:
        # inv() returns (forward_azimuth, back_azimuth, distance_in_meters)
        _, _, distance_m = cgcs2000.inv(float(lon1), float(lat1), float(lon2), float(lat2))
        return distance_m / 1000.0
    except (ValueError, TypeError):
        return float('inf')


def round_coordinates(lat, lon):
    """
    Round latitude and longitude to COORDINATE_PRECISION decimal places.
    Returns a tuple (rounded_lat, rounded_lon) or None if invalid.
    """
    try:
        if pd.isna(lat) or pd.isna(lon):
            return None
        return (round(float(lat), COORDINATE_PRECISION), round(float(lon), COORDINATE_PRECISION))
    except (ValueError, TypeError):
        return None


def get_neighboring_buckets(lat, lon, max_distance_km):
    """
    Get the coordinates of the bucket and all neighboring buckets needed to cover max_distance_km.
    Returns a list of (rounded_lat, rounded_lon) tuples.
    """
    coords = round_coordinates(lat, lon)
    if not coords:
        return []

    base_lat, base_lon = coords
    step = 10 ** (-COORDINATE_PRECISION)

    # Number of buckets to search on each side. With 1-degree buckets and 50 km this is 1, which covers 50 km
    # everywhere in China: a degree of latitude is ~111 km, a degree of longitude at least ~67 km (up to 53°N)
    num_steps = int(max_distance_km / (step * 111)) + 1

    return [(round(base_lat + dlat * step, COORDINATE_PRECISION), round(base_lon + dlon * step, COORDINATE_PRECISION))
            for dlat in range(-num_steps, num_steps + 1)
            for dlon in range(-num_steps, num_steps + 1)]


def find_nearby_firms(treatment_df, untreated_df, max_distance_km=MAX_DISTANCE_KM):
    """
    For each treatment firm, find untreated firms within the specified distance.
    Uses spatial indexing for efficiency, then calculates actual distances.

    Returns:
    - nearby_firms: dict mapping treatment firm index to list of (untreated_idx, distance_km) tuples
    - untreated_to_treatment: dict mapping untreated firm index to list of (treatment_idx, distance_km) tuples
    """
    untreated_lat = untreated_df['纬度'].tolist()
    untreated_lon = untreated_df['经度'].tolist()

    # Spatial index: (rounded_lat, rounded_lon) -> list of untreated firm indices
    untreated_index = defaultdict(list)
    for idx, (lat, lon) in enumerate(zip(untreated_lat, untreated_lon)):
        coords = round_coordinates(lat, lon)
        if coords:
            untreated_index[coords].append(idx)

    nearby_firms = {}
    untreated_to_treatment = defaultdict(list)  # Track which treatment firms are near each untreated firm

    for idx, row in treatment_df.iterrows():
        if pd.isna(row['纬度']) or pd.isna(row['经度']):
            continue
        treatment_lat = float(row['纬度'])
        treatment_lon = float(row['经度'])

        # Collect candidate firms from all neighboring buckets
        candidates = []
        for bucket in get_neighboring_buckets(treatment_lat, treatment_lon, max_distance_km):
            candidates.extend(untreated_index.get(bucket, []))

        # Calculate actual distances for candidates
        nearby_list = []
        for untreated_idx in candidates:
            distance = haversine_distance(treatment_lat, treatment_lon,
                                          untreated_lat[untreated_idx], untreated_lon[untreated_idx])
            if distance <= max_distance_km:
                nearby_list.append((untreated_idx, distance))
                untreated_to_treatment[untreated_idx].append((idx, distance))

        if nearby_list:
            nearby_firms[idx] = nearby_list

    return nearby_firms, untreated_to_treatment


def firm_columns(prefix, row=None):
    """Output columns for one firm (empty strings when there is no firm, e.g. no renewable plant nearby)."""
    get = (lambda col: row.get(col, '')) if row is not None else (lambda col: '')
    return {
        f'{prefix}_org_code': get('组织机构代码'),
        f'{prefix}_name': get('企业名称'),
        f'{prefix}_省': get('省'),
        f'{prefix}_市': get('市'),
        f'{prefix}_区县': get('区县'),
        f'{prefix}_lon': get('经度'),
        f'{prefix}_lat': get('纬度'),
    }


def main():
    # Check command line arguments
    if len(sys.argv) < 4 or sys.argv[1] != 'input':
        print("Usage: python 16_find_nearby_firms_distances.py input <treatment_firms.csv> <untreated_firms.csv>")
        print("Both files are read from this script's inputs/ folder.")
        sys.exit(1)

    script_dir = Path(__file__).parent
    treatment_file = script_dir / 'inputs' / sys.argv[2]
    untreated_file = script_dir / 'inputs' / sys.argv[3]
    treatment_df = pd.read_csv(treatment_file, encoding='utf-8', dtype=str)
    untreated_df = pd.read_csv(untreated_file, encoding='utf-8', dtype=str)

    # Find nearby firms
    nearby_firms, untreated_to_treatment = find_nearby_firms(treatment_df, untreated_df)
    treatment_with_nearby = len(nearby_firms)
    total_matches = sum(len(nearby_list) for nearby_list in nearby_firms.values())
    num_nearby_untreated = len(untreated_to_treatment)
    print(f"{treatment_file.name}: {treatment_with_nearby:,} of {len(treatment_df):,} plants have a firm within "
          f"{MAX_DISTANCE_KM} km; {total_matches:,} plant-firm pairs, {num_nearby_untreated:,} of "
          f"{len(untreated_df):,} firms matched")

    # Detailed results: one row per plant-firm pair
    results = []
    for treatment_idx, nearby_list in nearby_firms.items():
        treatment_row = treatment_df.iloc[treatment_idx]
        for untreated_idx, distance in nearby_list:
            results.append({**firm_columns('renewable', treatment_row),
                            **firm_columns('untreated', untreated_df.iloc[untreated_idx]),
                            'distance_km': f"{distance:.3f}"})

    # Add unmatched firms (those not close to any renewable firm) with empty renewable columns
    num_unmatched = 0
    for idx, row in untreated_df.iterrows():
        if idx not in untreated_to_treatment:
            results.append({**firm_columns('renewable'), **firm_columns('untreated', row), 'distance_km': ''})
            num_unmatched += 1

    output_file = script_dir / 'outputs' / f"nearby_firms_{MAX_DISTANCE_KM}km_{treatment_file.stem}_vs_{untreated_file.stem}pyproj.csv"
    pd.DataFrame(results).to_csv(output_file, index=False, encoding='utf-8')
    print(f"Saved {output_file.name}: {len(results):,} rows "
          f"({len(results) - num_unmatched:,} pairs + {num_unmatched:,} firms with no plant nearby)")

    # Summary: proximity by distance (the paper's table of firms near renewable energy firms). Distances are taken
    # as written to the CSV (3 decimals), which is what the Stata do-files use for the distance rings.
    pairs = [(treatment_idx, untreated_idx, float(f"{dist:.3f}"))
             for treatment_idx, nearby_list in nearby_firms.items() for untreated_idx, dist in nearby_list]
    summary_file = script_dir / 'outputs' / f"summary_{MAX_DISTANCE_KM}km_{treatment_file.stem}_vs_{untreated_file.stem}pyproj.txt"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("PROXIMITY BY DISTANCE\n")
        f.write("="*80 + "\n\n")
        f.write(f"Treatment firms file: {treatment_file.name}\n")
        f.write(f"Untreated firms file: {untreated_file.name}\n\n")
        f.write("  Firms near = untreated firms with at least one treatment firm within the distance\n\n")
        f.write(f"  {'Distance':>8}  {'Firms near':>10}  {'Near 2+':>8}  {'% near 2+':>9}  {'Treatment firms':>15}  "
                f"{'Pairs':>7}  {'Treatment/firm':>14}  {'Firms/treatment':>15}\n")
        for band in [b for b in DISTANCE_BANDS_KM if b <= MAX_DISTANCE_KM]:
            within = [(t, u) for t, u, dist in pairs if dist <= band]
            treatments_per_firm = Counter(u for _, u in within)
            n_firms = len(treatments_per_firm)
            n_multi = sum(1 for count in treatments_per_firm.values() if count > 1)
            n_treatment = len({t for t, _ in within})
            f.write(f"  {f'{band} km':>8}  {n_firms:>10,}  {n_multi:>8,}  "
                    f"{(n_multi / n_firms * 100 if n_firms else 0):>8.2f}%  {n_treatment:>15,}  {len(within):>7,}  "
                    f"{(len(within) / n_firms if n_firms else 0):>14.2f}  "
                    f"{(len(within) / n_treatment if n_treatment else 0):>15.2f}\n")

    print(f"Saved {summary_file.name}")


if __name__ == "__main__":
    main()
