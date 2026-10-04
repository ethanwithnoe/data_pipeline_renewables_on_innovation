from pathlib import Path
import sys

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "inputs"
OUTPUT_DIR = BASE_DIR / "outputs"

# Panel variant, chosen on the command line:
#   python 19_join_data_together.py [main|nomulti|nomanual|placebo]   (default: main)
# Only the four input/output file choices change per variant; the merge logic is the same.
NEARBY_REAL = "nearby_firms_50km_geo_Realrenewable_firmsMC_full_address_addresses_vs_geo_SIPO_14yearfirms_full_address_FINALpyproj.csv"
# placebo plants = the ASIE_NONrenewableFirms2000-2013 list: boiler, engine and turbine makers (codes 3411/3412/3413, 1,080 plants)
NEARBY_PLACEBO = "nearby_firms_50km_geo_NonRenewable2013NamesFilled_cleaned_full_address_addresses_vs_geo_SIPO_14yearfirms_full_address_FINALpyproj.csv"
VARIANTS = {
    "main": dict(nearby=NEARBY_REAL, renew="ASIE_Renewables_Firms_2000-2013.csv",
                 patent="ASIE_firms_all_patents_cleaned_aggregated_14years.csv",
                 output="firm_patent_renewable50KM.csv"),
    "nomulti": dict(nearby=NEARBY_REAL, renew="ASIE_Renewables_Firms_2000-2013.csv",
                    patent="ASIE_firms_all_patents_cleaned_aggregated_14years_CONVERTEDNOMULTIASSIGNEE.csv",
                    output="firm_patent_NOMULTIASSIGNEE50KM.csv"),
    # NOMANUAL: renewable plants + patents without the 2010-2013 manual matches (all He et al. data kept)
    "nomanual": dict(nearby=NEARBY_REAL, renew="ASIE_Renewables_Firms_2000-2013.csv",
                     patent="ASIE_firms_all_patents_cleaned_aggregated_14years_NO_MANUAL_2010_2013.csv",
                     output="firm_patent_NOMANUAL50KM.csv"),
    "placebo": dict(nearby=NEARBY_PLACEBO, renew="ASIE_NONrenewableFirms2000-2013.csv",
                    patent="ASIE_firms_all_patents_cleaned_aggregated_14years.csv",   # same patents as main
                    output="firm_patent_PLACEBO50KM.csv"),
}
variant = sys.argv[1] if len(sys.argv) > 1 else "main"
files = VARIANTS[variant]
print(f"Variant: {variant}")
output_file = OUTPUT_DIR / files["output"]

# 1. Load the CSVs
firm_year = pd.read_csv(INPUT_DIR / "firm_14plus_years_2013_codes_converted.csv")
nearby = pd.read_csv(INPUT_DIR / files["nearby"])
renew = pd.read_csv(INPUT_DIR / files["renew"], encoding='utf-8')
patents = pd.read_csv(INPUT_DIR / files["patent"])
print(f"Loaded {len(firm_year):,} firm-year rows, {len(nearby):,} firm-plant pairs, "
      f"{len(renew):,} plants, {len(patents):,} patent rows")

# Rename columns for consistency
# Input columns:
# firm_year: firm_id, firm_name, year, sales_revenue, capital, opening_year, max_consecutive_years, firm_code
# nearby: renewable_org_code, renewable_name, renewable_省, renewable_市, renewable_区县, renewable_lon, renewable_lat,
#         untreated_org_code, untreated_name, untreated_省, untreated_市, untreated_区县, untreated_lon, untreated_lat, distance_km
# renew: 组织机构代码, 企业名称, 省自治区直辖市, 地区市州盟, 县区市旗, 街道办事处, 详细地址, 邮政编码,
#        开业成立时间年, 行业小类代码, 主要业务活动或主要产品1, 主要业务活动或主要产品2, 主要业务活动或主要产品3
# patents: asie_id, year, fullname, stemname, assignee, assignee_full, assignee_stem, 申请专利权人, 地址, 国省代码,
#          invention_patents, utility_patents, design_patents, total_patents
nearby = nearby.rename(columns={'untreated_org_code': 'firm_id', 'renewable_org_code': 'renw_id', 'distance_km': 'dist_km'})
renew = renew.rename(columns={'组织机构代码': 'renw_id', '开业成立时间年': 'open_year'})
patents = patents.rename(columns={'asie_id': 'firm_id'})

# Convert firm_id and renw_id to string to ensure consistent data types.
# Firms with no plant within 50 km (pure controls) get renw_id = 'nan'.
nearby['firm_id'] = nearby['firm_id'].astype(str)
nearby['renw_id'] = nearby['renw_id'].astype(str).fillna('nan')
renew['renw_id'] = renew['renw_id'].astype(str)
patents['firm_id'] = patents['firm_id'].astype(str)
firm_year['firm_id'] = firm_year['firm_id'].astype(str)

# Filter firm_year to only include firms in the patent dataset
patent_firm_ids = patents['firm_id'].unique()
firm_year = firm_year[firm_year['firm_id'].isin(patent_firm_ids)]
print(f"Kept {len(firm_year):,} firm-year rows for the {len(patent_firm_ids):,} firms with patent data")

# Convert all year columns to integers
firm_year['year'] = firm_year['year'].astype(int)
firm_year['opening_year'] = pd.to_numeric(firm_year['opening_year'], errors='coerce').fillna(0).astype(int)
renew['open_year'] = pd.to_numeric(renew['open_year'], errors='coerce').fillna(0).astype(int)
patents['year'] = patents['year'].astype(int)

# 2. Merge distance and renewable info
firm_renw = nearby.merge(renew[['renw_id', 'open_year']], on='renw_id', how='left')

# Drop firm-plant pairs that cannot be a valid treatment:
#   - the firm IS the plant (firm_id == renw_id; some placebo plants are themselves sample firms, at 0 km);
#   - the plant has no opening year (open_year missing/0 -> renewable_start_year 0 = "treated in every year").
# None of these occur in the real-renewable variants. A firm left with no pairs becomes a control row.
self_pair = firm_renw['firm_id'] == firm_renw['renw_id']
bad_pair = (firm_renw['renw_id'] != 'nan') & (self_pair | (firm_renw['open_year'].fillna(0) == 0))
print(f"Dropping {int(bad_pair.sum()):,} invalid firm-plant pairs (self-pairs: {int(self_pair.sum()):,})")
firm_renw = firm_renw[~bad_pair]

# 3. Build the firm-year-renewable dataset
firm_renw_year = firm_renw.merge(firm_year, on='firm_id', how='right')
# Firms whose every pair was dropped above come out of the right-merge with a missing renw_id;
# label them like the other pure controls ('nan')
firm_renw_year['renw_id'] = firm_renw_year['renw_id'].fillna('nan')

# 3.5. Merge patent data (only the patent columns we need); fill missing patent values with 0
patent_count_cols = ['invention_patents', 'utility_patents', 'design_patents', 'total_patents']
firm_renw_year = firm_renw_year.merge(patents[['firm_id', 'year'] + patent_count_cols], on=['firm_id', 'year'], how='left')
for col in patent_count_cols:
    firm_renw_year[col] = firm_renw_year[col].fillna(0).astype(int)

# 4. Select and organize final columns
# Select columns to keep - including both firm names, renewable info, distance, city info, patent data, and employees
final_panel = firm_renw_year[[
    'firm_id',
    'firm_name',
    'year',
    'renw_id',
    'firm_code',
    'firm_code_raw',      # year-varying original code; firm_code is the firm's modal code
    'renewable_name',
    'renewable_市',
    'renewable_区县',
    'untreated_市',
    'untreated_区县',
    'dist_km',
    'open_year',
    'sales_revenue',
    'capital',
    'opening_year',
    'max_consecutive_years',
    'employees',
] + patent_count_cols]

# Rename columns for clarity
final_panel = final_panel.rename(columns={
    'renewable_name': 'renewable_firm_name',
    'renewable_市': 'renewable_city',
    'renewable_区县': 'renewable_district',
    'untreated_市': 'firm_city',
    'untreated_区县': 'firm_district',
    'dist_km': 'distance_km',
    'open_year': 'renewable_start_year',
    'opening_year': 'firm_opening_year'
})

# Convert renewable_start_year, employees and the industry codes to integers (filling NaN with 0 first)
for col in ['renewable_start_year', 'employees', 'firm_code', 'firm_code_raw']:
    final_panel[col] = pd.to_numeric(final_panel[col], errors='coerce').fillna(0).astype(int)

# Sort by firm_id and year
final_panel = final_panel.sort_values(['firm_id', 'year']).reset_index(drop=True)

# 5. Export to CSV
final_panel.to_csv(output_file, index=False, encoding='utf-8-sig')
print(f"Saved {output_file.name}: {len(final_panel):,} rows, {final_panel['firm_id'].nunique():,} firms, "
      f"{final_panel['renw_id'].nunique():,} plant ids, years {final_panel['year'].min()}-{final_panel['year'].max()}")
print(f"Patent totals: invention {final_panel['invention_patents'].sum():,}, utility {final_panel['utility_patents'].sum():,}, "
      f"design {final_panel['design_patents'].sum():,}, all {final_panel['total_patents'].sum():,}")

# Checks: every firm in the patent data is in the panel, and every firm has all 14 years
n_firms = final_panel['firm_id'].nunique()
n_patent_firms = patents['firm_id'].nunique()
if n_firms == n_patent_firms:
    print(f"Check: all {n_patent_firms:,} patent-data firms are in the output")
else:
    print(f"WARNING: firm counts do not match (patent data {n_patent_firms:,}, output {n_firms:,})")

n_firm_years = final_panel.groupby(['firm_id', 'year']).ngroups
if n_firm_years == n_firms * 14:
    print(f"Check: all {n_firms:,} firms have 14 years of data")
else:
    print(f"WARNING: {n_firm_years:,} firm-years, expected {n_firms * 14:,} (14 per firm)")
