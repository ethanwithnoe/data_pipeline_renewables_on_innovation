import pandas as pd
from pathlib import Path
from collections import defaultdict

# ============================================================================
# INPUT COLUMN NAMES (Chinese column names from ASIE data)
# ============================================================================
INPUT_COLUMNS = {
    'firm_id': '组织机构代码',
    'firm_name': '企业名称',
    'capital': '资产总计千元',
    'opening_year': '开业成立时间年',  # Not available in all years
    'employee_2000_2009': '全部从业人员年平均人数人',  # Used in 2000-2009
    'employee_2010_2013': '年末从业人员合计人',  # Used in 2010-2013
    'sales_2000_2009': '主营业务产品销售收入千元',  # Used in 2000-2009, 2011-2013
    'sales_2010': '营业收入合计千元',  # Used only in 2010
    'firm_code': '行业小类代码'
}

# Get the script directory
script_dir = Path(__file__).parent
asie_csv_dir = script_dir / "inputs" / "ASIE_csv"

print("Loading ASIE data from 2000 to 2013...")

# Dictionary to store which years each firm appears in
firm_years = defaultdict(set)
# List to store firm characteristics for each firm-year combination
firm_characteristics_list = []

# Load each year's data
for year in range(2000, 2014):
    asie_file = asie_csv_dir / f"ASIE_{year}.csv"
    if not asie_file.exists():
        print(f"Warning: file not found: {asie_file.name}")
        continue

    # First, read just the header to check which employee column exists
    header_df = pd.read_csv(asie_file, nrows=0)

    # Determine which employee column to use
    if INPUT_COLUMNS['employee_2000_2009'] in header_df.columns:
        employee_col = INPUT_COLUMNS['employee_2000_2009']
    elif INPUT_COLUMNS['employee_2010_2013'] in header_df.columns:
        employee_col = INPUT_COLUMNS['employee_2010_2013']
    else:
        print(f"Warning: {year}: no employee column found")
        continue

    # Determine which sales column to use (2010 uses different column)
    if year == 2010:
        sales_col = INPUT_COLUMNS['sales_2010']
    else:
        sales_col = INPUT_COLUMNS['sales_2000_2009']

    # Load the data with all needed columns
    cols_to_load = [INPUT_COLUMNS['firm_id'], INPUT_COLUMNS['firm_name'],
                    sales_col, INPUT_COLUMNS['capital'], employee_col, INPUT_COLUMNS['firm_code']]

    # Check for missing required columns
    missing_required = [col for col in cols_to_load if col not in header_df.columns]
    if missing_required:
        print(f"Error: {year}: missing required columns: {missing_required}")
        continue

    # Check if opening_year column exists (optional)
    has_opening_year = INPUT_COLUMNS['opening_year'] in header_df.columns
    if has_opening_year:
        cols_to_load.append(INPUT_COLUMNS['opening_year'])

    asie_df = pd.read_csv(asie_file, dtype={INPUT_COLUMNS['firm_id']: str},
                          low_memory=False, usecols=cols_to_load)

    # Get opening year if available
    if has_opening_year:
        asie_df['opening_year'] = pd.to_numeric(asie_df[INPUT_COLUMNS['opening_year']], errors='coerce')
    else:
        asie_df['opening_year'] = None

    # Filter to only include firms with all three values > 0
    asie_df = asie_df[
        (pd.to_numeric(asie_df[sales_col], errors='coerce') > 0) &
        (pd.to_numeric(asie_df[INPUT_COLUMNS['capital']], errors='coerce') > 0) &
        (pd.to_numeric(asie_df[employee_col], errors='coerce') > 0)
    ]
    print(f"{year}: {asie_df[INPUT_COLUMNS['firm_id']].nunique():,} unique firms")

    # Record which year each firm appears in and save characteristics
    for _, row in asie_df.iterrows():
        firm_id = row[INPUT_COLUMNS['firm_id']]
        if pd.notna(firm_id):
            firm_years[firm_id].add(year)

            # Store firm characteristics for this year
            firm_characteristics_list.append({
                'firm_id': firm_id,
                'firm_name': row[INPUT_COLUMNS['firm_name']],
                'year': year,
                'sales_revenue': row[sales_col],
                'capital': row[INPUT_COLUMNS['capital']],
                'employees': row[employee_col],
                'opening_year': row['opening_year'],
                'firm_code': row[INPUT_COLUMNS['firm_code']]
            })


def find_longest_consecutive_years(years_set):
    """Find the longest consecutive sequence of years."""
    if not years_set:
        return 0, []

    sorted_years = sorted(years_set)
    max_sequence = [sorted_years[0]]
    current_sequence = [sorted_years[0]]

    for i in range(1, len(sorted_years)):
        if sorted_years[i] == sorted_years[i-1] + 1:
            # Consecutive year
            current_sequence.append(sorted_years[i])
        else:
            # Gap in years
            if len(current_sequence) > len(max_sequence):
                max_sequence = current_sequence
            current_sequence = [sorted_years[i]]

    # Check final sequence
    if len(current_sequence) > len(max_sequence):
        max_sequence = current_sequence

    return len(max_sequence), max_sequence


# Longest run of consecutive years for every firm
longest_run = {firm_id: find_longest_consecutive_years(years) for firm_id, years in firm_years.items()}

# Firms appearing in ALL years consecutively (2000-2013)
firms_all_years = [firm_id for firm_id, (max_consecutive, _) in longest_run.items() if max_consecutive == 14]
print(f"Unique firms: {len(firm_years):,}; appearing in all 14 years consecutively (2000-2013): {len(firms_all_years):,}")

# Save results
results_list = []
for firm_id, years in firm_years.items():
    max_consecutive, consecutive_sequence = longest_run[firm_id]
    results_list.append({
        'firm_id': firm_id,
        'num_years': len(years),
        'max_consecutive_years': max_consecutive,
        'consecutive_sequence': f"{consecutive_sequence[0]}-{consecutive_sequence[-1]}" if consecutive_sequence else "",
        'all_years': ','.join(map(str, sorted(years))),
        'appears_all_consecutive': max_consecutive == 14
    })

results_df = pd.DataFrame(results_list)
results_df = results_df.sort_values('max_consecutive_years', ascending=False)
results_df.to_csv(script_dir / "outputs" / "firms_across_years_analysis.csv", index=False)

# ============================================================================
# Create firm characteristics CSV with max_consecutive_years
# ============================================================================

# Create DataFrame from collected characteristics
firm_chars_df = pd.DataFrame(firm_characteristics_list)

# Some ASIE year files list the same firm twice in one year (mostly 2009, with different sales). Keep the
# first record in the year file's order so no firm-year is double-counted.
n_before = len(firm_chars_df)
firm_chars_df = firm_chars_df.drop_duplicates(subset=['firm_id', 'year'], keep='first')
print(f"Duplicate firm-year records dropped: {n_before - len(firm_chars_df):,}")

# Add max_consecutive_years to each row
firm_chars_df['max_consecutive_years'] = firm_chars_df['firm_id'].map(lambda firm_id: longest_run[firm_id][0])

# Convert columns to appropriate types (keep sales_revenue and capital as floats, employees as integer)
firm_chars_df['year'] = firm_chars_df['year'].astype(int)
firm_chars_df['sales_revenue'] = pd.to_numeric(firm_chars_df['sales_revenue'], errors='coerce')
firm_chars_df['capital'] = pd.to_numeric(firm_chars_df['capital'], errors='coerce')
firm_chars_df['employees'] = pd.to_numeric(firm_chars_df['employees'], errors='coerce').fillna(0).astype(int)
firm_chars_df['opening_year'] = pd.to_numeric(firm_chars_df['opening_year'], errors='coerce')
firm_chars_df['max_consecutive_years'] = firm_chars_df['max_consecutive_years'].astype(int)
# Do not convert firm_code to int; it may contain non-numeric values
# Sort by firm_id and year
firm_chars_df = firm_chars_df.sort_values(['firm_id', 'year'])

# Save to CSV
characteristics_file = script_dir / "outputs" / "firm_characteristics_by_year.csv"
firm_chars_df.to_csv(characteristics_file, index=False, encoding='utf-8')
print(f"Saved {len(firm_chars_df):,} firm-year observations "
      f"({firm_chars_df['firm_id'].nunique():,} firms) to {characteristics_file.name}")

# Same rows for the firms with 14 consecutive years only. This is the file stage 6 reads (it keeps only these
# firms anyway), and it is small enough to share in place of the raw ASIE data.
long_firms_df = firm_chars_df[firm_chars_df['max_consecutive_years'] >= 14]
long_firms_df.to_csv(script_dir / "outputs" / "firm_characteristics_14year_firms.csv", index=False, encoding='utf-8')
print(f"Saved {len(long_firms_df):,} rows ({long_firms_df['firm_id'].nunique():,} firms with 14 consecutive years) "
      f"to firm_characteristics_14year_firms.csv")

# Validation check: total years × firm count = total rows
expected_total_rows = sum(len(years) for years in firm_years.values())
if expected_total_rows == len(firm_chars_df):
    print("Validation passed: row count = years × firms")
else:
    print(f"VALIDATION FAILED: Difference = {len(firm_chars_df) - expected_total_rows:,} rows")

# Create CSV with 2013 data for firms that existed all 14 years
asie_2013_df = pd.read_csv(asie_csv_dir / "ASIE_2013.csv", dtype={'组织机构代码': str}, low_memory=False, encoding='utf-8')

# Filter to only firms that exist all 14 years
firms_2013_data = asie_2013_df[asie_2013_df['组织机构代码'].isin(firms_all_years)]
firms_2013_data.to_csv(script_dir / "outputs" / "firms_2013_data.csv", index=False, encoding='utf-8')
print(f"Saved {len(firms_2013_data):,} rows to firms_2013_data.csv")
