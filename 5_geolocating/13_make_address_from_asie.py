import pandas as pd
import sys
from pathlib import Path
import re

def remove_symbols(address):
    """
    Remove special characters and symbols from address.
    Removes punctuation, brackets, quotation marks, and other non-address symbols.
    """
    if pd.isna(address) or address == '':
        return ''
    
    address = str(address).strip()
    
    # Comprehensive list of symbols to remove
    symbols_to_remove = [
        # Chinese parentheses and brackets
        '（', '）', '【', '】', '「', '」', '『', '』', '〔', '〕', '〈', '〉', '《', '》',
        # English parentheses and brackets (half-width and full-width)
        '(', ')', '[', ']', '{', '}', '<', '>',
        # Quotation marks
        '"', '"', '"', "'", "'", "'", '\'', '"', '`', '´',
        # DONT REMOVE Dashes and hyphens
        # '-', '—', '–', '－', '﹣', '‐', '‑', '‒', '―', '⁃',
        # Slashes
        '/', '\\', '／', '＼',
        # Punctuation marks
        ',', '，', '、', ';', '；', ':', '：', '.', '。', '·', '•', '‧',
        # Question and exclamation marks
        '?', '？', '!', '！', '‼', '⁇', '⁈', '⁉',
        # Ampersands and symbols
        '&', '＆', '@', '＠', '#', '＃', '*', '＊', '※',
        # Plus, minus, equals
        '+', '＋', '=', '＝', '±',
        # Percent and dollar
        '%', '％', '$', '＄', '¥', '￥', '€', '£',
        # Degree and other symbols
        '°', '℃', '℉', '§', '¶', '†', '‡',
        # Vertical bars and pipes
        '|', '｜', '¦',
        # Tildes and carets
        '~', '～', '^', '＾',
        # Underscores
        '_', '＿',
        # Other Chinese punctuation
        '…', '⋯', '﹏', '︰', '﹕', '︱', '︳', '︴', '﹀', '﹁', '﹂', '﹃', '﹄',
        # Special spaces and separators
        '\u3000',  # Ideographic space
        '\xa0',    # Non-breaking space
        ' ',       # Regular space
        '\t',      # Tab
    ]
    
    # Remove all symbols
    for symbol in symbols_to_remove:
        address = address.replace(symbol, '')
    
    # Remove any remaining whitespace
    address = re.sub(r'\s+', '', address)
    
    return address.strip()


def extract_location_name(location_str):
    """
    Extract the core name from a location string by removing suffixes like 省/市/区/县/自治区/直辖市/州/盟/旗
    For example: '山东省' -> '山东', '潍坊市' -> '潍坊', '海陵区' -> '海陵'
    """
    if pd.isna(location_str) or location_str == '':
        return ''

    location_str = str(location_str).strip()

    # Remove common administrative suffixes
    suffixes = ['自治区', '省', '直辖市', '市', '区', '县', '州', '盟', '旗']

    for suffix in suffixes:
        if location_str.endswith(suffix):
            return location_str[:-len(suffix)]

    return location_str


def add_missing_suffix(result, core, full_name):
    """If the core name (e.g. '潍坊') is in the address but the full name ('潍坊市') is not, add the suffix.
    Don't replace when the core is already followed by a suffix, which would create duplicates like "上海市市"."""
    if full_name not in result:
        result = re.sub(core + r'(?![省市区县州盟旗])', full_name, result, count=1)
    return result


def insert_after(result, anchors, text):
    """Insert text right after the first anchor found in the address, or at the beginning if none is found."""
    for anchor in anchors:
        if anchor and anchor in result:
            insert_pos = result.find(anchor) + len(anchor)
            return result[:insert_pos] + text + result[insert_pos:]
    return text + result


def build_full_address(row):
    """
    Build a full address by intelligently combining administrative divisions with detailed address.
    - Avoids duplicates when city and district are the same
    - Adds administrative suffixes (省/市/区/县) when core names exist but suffixes are missing
    - Maintains proper order: province -> city -> district
    """
    province = str(row['省自治区直辖市']) if pd.notna(row['省自治区直辖市']) else ''
    city = str(row['地区市州盟']) if pd.notna(row['地区市州盟']) else ''
    district = str(row['县区市旗']) if pd.notna(row['县区市旗']) else ''
    detail = str(row['详细地址']) if pd.notna(row['详细地址']) else ''

    # Extract core names for matching
    province_core = extract_location_name(province)
    city_core = extract_location_name(city)
    district_core = extract_location_name(district)

    # Check if this is a direct-controlled municipality (province and city are effectively the same)
    is_municipality = province_core in ['北京', '上海', '天津', '重庆']

    # Check if city and district are the same (avoid duplicates)
    city_district_same = (city_core == district_core and city_core != '')

    # Start with detail address
    result = detail

    # Step 1: Handle province
    if province_core:
        if province_core in result:
            result = add_missing_suffix(result, province_core, province)
        else:
            # Province not in address, add at beginning
            result = province + result

    # Step 2: Handle city
    # For municipalities, city is often just the district, so skip if it's a district name
    if city_core and not is_municipality:
        if city_core in result:
            result = add_missing_suffix(result, city_core, city)
        else:
            # City not in address, add after province
            result = insert_after(result, [province], city)

    # Step 3: Handle district
    # Skip if city and district are the same (already handled in city step)
    if district_core and not city_district_same:
        if district_core in result:
            result = add_missing_suffix(result, district_core, district)
        elif city and not is_municipality:
            # District not in address, add after city (or after province if the city is not found)
            result = insert_after(result, [city, province], district)
        else:
            # Add after province (no city, or a municipality)
            result = insert_after(result, [province], district)

    return result


def main():
    # Check command line arguments
    if len(sys.argv) < 3 or sys.argv[1] != 'input':
        print("Usage: python 13_make_address_from_asie.py input <input_file.csv>")
        print("The file is read from this script's inputs/ folder (or give an absolute path).")
        sys.exit(1)

    # Resolve the input file: an absolute path, or a file in this script's inputs/ folder
    script_dir = Path(__file__).parent
    input_file = Path(sys.argv[2])
    if not input_file.is_absolute():
        input_file = script_dir / 'inputs' / sys.argv[2]

    # Load the CSV
    df = pd.read_csv(input_file, encoding='utf-8', dtype=str)

    # Build full addresses, then clean them (remove symbols ONLY)
    df['full_address'] = df.apply(build_full_address, axis=1).apply(remove_symbols)

    # Create output DataFrame with required columns
    output_df = df[['组织机构代码', '企业名称', '省自治区直辖市', '地区市州盟', '县区市旗', 'full_address']]

    # Save to CSV, named after the input file
    output_file = script_dir / "outputs" / f"{input_file.stem}_full_address.csv"
    output_df.to_csv(output_file, index=False, encoding='utf-8')
    print(f"Built full addresses for {len(output_df):,} firms; saved {output_file.name}")


if __name__ == "__main__":
    main()
