import pandas as pd
import requests
import sys
import time
import json
from pathlib import Path
from dotenv import load_dotenv
import os


def geocode_address(address, api_key, city=None):
    """
    Geocode an address using Gaode API

    Args:
        address: The full address to geocode
        api_key: Gaode API key
        city: Optional city to narrow search

    Returns:
        Dictionary with full API response or error info
    """
    params = {
        'key': api_key,
        'address': address,
        'output': 'JSON'
    }
    if city:
        params['city'] = city

    try:
        response = requests.get("https://restapi.amap.com/v3/geocode/geo", params=params, timeout=10)
        response.raise_for_status()
        # Return the full API response
        return response.json()
    except Exception as e:
        # Return error information in similar structure
        return {
            'status': '0',
            'info': f'Error: {str(e)}',
            'infocode': 'ERROR',
            'count': '0',
            'geocodes': []
        }


def main():
    # Check command line arguments
    if len(sys.argv) < 3 or sys.argv[1] != 'input':
        print("Usage: python 14_gaodelocate.py input <input_file.csv>")
        print("The file is read from this script's inputs/ folder (or give an absolute path);")
        print("the geocode JSON is written to outputs/. Needs GAODE_KEY in 5_geolocating/.env.")
        sys.exit(1)

    script_dir = Path(__file__).parent

    # Load the API key from the .env file
    env_file = script_dir / '.env'
    load_dotenv(env_file)
    api_key = os.getenv('GAODE_KEY')
    if not api_key:
        print(f"Error: GAODE_KEY not found. Please add GAODE_KEY=your_key_here to {env_file}")
        sys.exit(1)

    # Resolve the input file: an absolute path, or a file in this script's inputs/ folder
    input_file = Path(sys.argv[2])
    if not input_file.is_absolute():
        input_file = script_dir / 'inputs' / sys.argv[2]
    output_folder = script_dir / 'outputs'
    output_folder.mkdir(exist_ok=True)

    # Load the CSV
    df = pd.read_csv(input_file, encoding='utf-8', dtype=str)

    # Check for address column (full_address or 完整地址)
    if 'full_address' in df.columns:
        address_col = 'full_address'
    elif '完整地址' in df.columns:
        address_col = '完整地址'
    else:
        print("Error: Neither 'full_address' nor '完整地址' column found")
        sys.exit(1)

    print(f"Geocoding {len(df):,} addresses from {input_file.name} with the Gaode API (0.4 s between requests)")
    output_file = output_folder / f"geo_{input_file.stem}.json"

    # Checkpointing: each row's result is appended to a sidecar .jsonl the instant it completes (one flushed line
    # per row, keyed by 组织机构代码). A restart reads this file first and skips every row already done, so no API
    # call is ever repeated (or paid for twice), and an interruption loses at most the row in flight. The final
    # geo_<stem>.json array (read by 15_geocode_json_to_csv.py) is assembled from it at the end, in input row order.
    checkpoint_file = output_folder / f"geo_{input_file.stem}.checkpoint.jsonl"

    def row_key(idx, row):
        code = row.get('组织机构代码', None)
        return str(code) if pd.notna(code) and str(code).strip() else f"__row_{idx}"

    done = {}
    if checkpoint_file.exists():
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            for line_no, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    print(f"Warning: skipping unreadable checkpoint line {line_no} (likely a partial write from an interrupted run)")
                    continue
                done[row_key(entry.get('__idx', -1), {'组织机构代码': entry.get('组织机构代码')})] = entry
        print(f"Resuming from checkpoint: {len(done):,} rows already geocoded (their API calls will be skipped)")

    # Track statistics (over the WHOLE dataset: rows resumed from checkpoint + rows geocoded this run)
    success_count = 0
    failed_count = 0
    multiple_results = 0
    resumed_count = 0
    fresh_count = 0
    all_entries = []  # in original row order, for the final array

    with open(checkpoint_file, 'a', encoding='utf-8') as ckpt:
        for idx, row in df.iterrows():
            key = row_key(idx, row)

            if key in done:
                result_entry = done[key]
                resumed_count += 1
            else:
                city = row.get('地区市州盟', None) if '地区市州盟' in df.columns else None

                # Geocode, then combine original row data with the API response
                api_response = geocode_address(row[address_col], api_key, city)
                result_entry = {'__idx': idx}
                result_entry.update(row.to_dict())
                for field, default in [('status', ''), ('info', ''), ('infocode', ''), ('count', ''), ('geocodes', [])]:
                    result_entry[field] = api_response.get(field, default)

                # Checkpoint immediately: one complete, flushed line per row
                ckpt.write(json.dumps(result_entry, ensure_ascii=False) + '\n')
                ckpt.flush()
                os.fsync(ckpt.fileno())
                fresh_count += 1

                # Sleep to avoid rate limiting (max 3 requests per second) -- only for a real API call
                time.sleep(0.4)

            if result_entry.get('status') == '1':
                success_count += 1
            else:
                failed_count += 1
            if int(result_entry.get('count') or '0') > 1:
                multiple_results += 1
            all_entries.append(result_entry)

            # Show progress (based on rows processed this run, i.e. fresh + resumed so far)
            if (idx + 1) % 10 == 0 or (idx + 1) == len(df):
                print(f"Progress: {idx + 1}/{len(df)} ({(idx + 1)/len(df)*100:.1f}%) "
                      f"[fresh: {fresh_count}, resumed: {resumed_count}, "
                      f"failed so far: {failed_count} ({failed_count/(idx + 1)*100:.1f}%)]")

    # Assemble the final array in the original script's exact format (15_geocode_json_to_csv.py is unaffected)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('[\n')
        for i, entry in enumerate(all_entries):
            clean_entry = {k: v for k, v in entry.items() if k != '__idx'}
            if i > 0:
                f.write(',\n')
            json_str = json.dumps(clean_entry, ensure_ascii=False, indent=2)
            f.write('\n'.join('  ' + line for line in json_str.split('\n')))
        f.write('\n]')

    print(f"Geocoding completed: {success_count} succeeded, {failed_count} failed, {multiple_results} with multiple "
          f"geocodes ({fresh_count} API calls this run, {resumed_count} resumed from checkpoint)")
    print(f"Saved {output_file.name} (checkpoint {checkpoint_file.name} can be deleted once you are satisfied)")


if __name__ == "__main__":
    main()
