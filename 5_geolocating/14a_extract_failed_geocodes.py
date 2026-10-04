import json
import csv
import sys
from pathlib import Path

FIELDNAMES = ['组织机构代码', '企业名称', '省自治区直辖市', '地区市州盟', '县区市旗', 'full_address']


def extract_failed_geocodes(input_path, output_path):
    """
    Extract entries with failed geocoding from a JSON file and save to CSV.

    Args:
        input_path: Path to input JSON file with geocoding results
        output_path: Path to output CSV file
    """
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Failed if status is not '1' (success in Gaode API)
    failed_entries = [{field: entry.get(field, '') for field in FIELDNAMES}
                      for entry in data if entry.get('status', '') != '1']
    print(f"{input_path.name}: {len(failed_entries)} of {len(data):,} geocodes failed")

    # Write CSV
    if failed_entries:
        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(failed_entries)
        print(f"   saved them to {output_path.name} for a manual retry")


def main():
    # Check command line arguments
    if len(sys.argv) < 3 or sys.argv[1] != 'input':
        print("Usage: python 14a_extract_failed_geocodes.py input <input_file.json>")
        print("The file is read from this script's inputs/ folder; the CSV is written to outputs/.")
        sys.exit(1)

    script_dir = Path(__file__).parent
    input_path = script_dir / 'inputs' / sys.argv[2]
    output_folder = script_dir / 'outputs'
    output_folder.mkdir(exist_ok=True)

    # Create output filename (remove 'geo_' prefix if present)
    output_path = output_folder / (input_path.stem.removeprefix('geo_') + '_failed.csv')
    extract_failed_geocodes(input_path, output_path)


if __name__ == '__main__':
    main()
