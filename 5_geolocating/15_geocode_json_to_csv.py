import json
import csv
import sys
from pathlib import Path

# Address level hierarchy (from most specific to least specific)
# Lower number = more specific = higher priority
LEVEL_PRIORITY = {
    '门址': 1,           # door address
    '门牌号': 2,         # house number
    '单元号': 3,         # unit number
    '道路交叉路口': 4,   # road intersection
    '公交地铁站点': 5,    # subway station
    '道路': 5,           # road
    '兴趣点': 6,         # point of interest
    '小巷': 7,           # alley
    '住宅区': 8,         # residential area
    '村庄': 9,           # village
    '乡镇': 10,          # township
    '开发区': 11,        # development zone
    '区县': 12,          # district/county
    '市': 20,            # city
    '省': 50,            # province
    '国家': 75,          # country
    '未知': 99           # unknown
}


def level_priority(geocode):
    """Priority of a geocode's address level (unknown levels get 99, with a warning)."""
    level = geocode.get('level', '未知')
    if level not in LEVEL_PRIORITY:
        print(f"WARNING: Unknown address level '{level}' not in LEVEL_PRIORITY. Using default priority 99.")
        print(f"   Please add this level to LEVEL_PRIORITY dictionary.")
        return 99
    return LEVEL_PRIORITY[level]


def get_best_geocode(geocodes):
    """
    Select the best (most specific) geocode from a list of geocodes.
    Returns the geocode with the highest priority level.
    If levels are the same, returns the first one.
    Returns None if the list is empty.
    """
    if not geocodes:
        return None
    return min(geocodes, key=level_priority)


def first_if_list(value):
    """Gaode returns an empty list instead of a string for some missing fields."""
    if isinstance(value, list):
        return value[0] if value else ''
    return value


def process_json_file(input_path, output_path):
    """
    Process a JSON file with geocoding data and extract the best address for each entry.

    Args:
        input_path: Path to input JSON file
        output_path: Path to output CSV file
    """
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    csv_rows = []
    for entry in data:
        # Select best geocode (an empty dict when there are no geocodes)
        best = get_best_geocode(entry.get('geocodes', [])) or {}

        # Split location into longitude and latitude
        location = best.get('location', '')
        parts = location.split(',') if location else []

        csv_rows.append({
            '组织机构代码': entry.get('组织机构代码', ''),
            '企业名称': entry.get('企业名称', ''),
            '输入省': entry.get('省自治区直辖市', ''),
            '输入市': entry.get('地区市州盟', ''),
            '输入区县': entry.get('县区市旗', ''),
            '输入完整地址': entry.get('full_address', ''),
            '地理编码状态': entry.get('status', ''),
            '地理编码信息': entry.get('info', ''),
            '匹配数量': entry.get('count', ''),
            '最佳地址': best.get('formatted_address', ''),
            '地址级别': best.get('level', ''),
            # Geocode-specific administrative divisions (may be more accurate than input)
            '省': best.get('province', ''),
            '市': best.get('city', ''),
            '区县': best.get('district', ''),
            '街道': first_if_list(best.get('street', '')),
            '门牌号': first_if_list(best.get('number', '')),
            '行政区划代码': best.get('adcode', ''),
            '经度': parts[0] if len(parts) > 0 else '',
            '纬度': parts[1] if len(parts) > 1 else '',
            '坐标': location
        })

    # Write CSV
    if not csv_rows:
        print("Error: no data to write")
        return
    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()))
        writer.writeheader()
        writer.writerows(csv_rows)
    print(f"{input_path.name}: {len(csv_rows):,} entries saved to {output_path.name}")


def main():
    # Check command line arguments
    if len(sys.argv) < 3 or sys.argv[1] != 'input':
        print("Usage: python 15_geocode_json_to_csv.py input <input_file.json>")
        print("The file is read from this script's inputs/ folder; the CSV is written to outputs/.")
        sys.exit(1)

    script_dir = Path(__file__).parent
    input_path = script_dir / 'inputs' / sys.argv[2]
    output_folder = script_dir / 'outputs'
    output_folder.mkdir(exist_ok=True)

    # Create output filename (replace .json with _addresses.csv)
    process_json_file(input_path, output_folder / (input_path.stem + '_addresses.csv'))


if __name__ == '__main__':
    main()
