import pandas as pd
from pathlib import Path

# Get the script directory
script_dir = Path(__file__).parent
asie_csv_dir = script_dir / "inputs" / "ASIE_csv"
outputs_dir = script_dir / "outputs"

firms_analysis_df = pd.read_csv(outputs_dir / "firms_across_years_analysis.csv", dtype={'firm_id': str})

# Get the list of firm IDs and their max_consecutive_years
target_firm_ids = set(firms_analysis_df['firm_id'].dropna())
# Create a mapping of firm_id to max_consecutive_years
firm_id_to_max_consecutive = dict(zip(firms_analysis_df['firm_id'], firms_analysis_df['max_consecutive_years']))
print(f"Found {len(target_firm_ids):,} firm IDs to search for")

print("Collecting firm names from ASIE 2000-2013...")

# Every firm_id + name + year combination
name_years = []

# Search through each year's data
for year in range(2000, 2014):
    asie_file = asie_csv_dir / f"ASIE_{year}.csv"
    if not asie_file.exists():
        print(f"Warning: {asie_file.name} not found")
        continue

    # Load only the columns we need
    asie_df = pd.read_csv(
        asie_file,
        dtype={'组织机构代码': str},
        low_memory=False,
        usecols=['组织机构代码', '企业名称']
    )

    # Filter to only include our target firm IDs
    asie_df = asie_df[asie_df['组织机构代码'].isin(target_firm_ids)]

    # Remove rows with missing values
    asie_df = asie_df.dropna(subset=['组织机构代码', '企业名称'])

    asie_df['year'] = year
    name_years.append(asie_df)
    print(f"{year}: {len(asie_df):,} matches found")

name_years = pd.concat(name_years).drop_duplicates()

# Create one record per unique firm_id + name combination, collecting all its years
results_df = (name_years.groupby(['组织机构代码', '企业名称'])['year']
              .apply(lambda years: ','.join(map(str, sorted(years))))
              .reset_index(name='years'))
results_df['max_consecutive_years'] = results_df['组织机构代码'].map(firm_id_to_max_consecutive)

# Sort and save to CSV
results_df = results_df.sort_values(['max_consecutive_years', '组织机构代码', '企业名称'], ascending=[False, True, True])
output_file = outputs_dir / "unique_name_id_year_14year_firms.csv"
results_df.to_csv(output_file, index=False, encoding='utf-8')

# Count firms with multiple names
names_per_firm = results_df.groupby('组织机构代码').size()
print(f"Saved {len(results_df):,} firm_id + name rows for {len(names_per_firm):,} firms "
      f"({(names_per_firm > 1).sum():,} with more than one name) to {output_file.name}")
