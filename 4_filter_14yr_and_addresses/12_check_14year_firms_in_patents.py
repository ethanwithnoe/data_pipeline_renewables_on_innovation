import pandas as pd
from pathlib import Path
import sys

# Global variable for consecutive years threshold
CONSECUTIVE_YEARS_THRESHOLD = 14

# Patent variant to filter, chosen on the command line:
#   python 12_check_14year_firms_in_patents.py [all|nomulti|nomanual]   (default: all)
#   all      -> all patents        (feeds firm_patent_renewable50KM + firm_patent_PLACEBO50KM)
#   nomulti  -> single-assignee    (feeds firm_patent_NOMULTIASSIGNEE50KM)
#   nomanual -> own 2010-2013 manual matches dropped, all He et al. data kept (feeds firm_patent_NOMANUAL50KM)
PATENT_VARIANTS = {
    "all": ("ASIE_firms_all_patents_cleaned_aggregated.csv",
            "ASIE_firms_all_patents_cleaned_aggregated_14years.csv"),
    "nomulti": ("ASIE_firms_all_patents_cleaned_aggregated_CONVERTEDNOMULTIASSIGNEE.csv",
                "ASIE_firms_all_patents_cleaned_aggregated_14years_CONVERTEDNOMULTIASSIGNEE.csv"),
    "nomanual": ("ASIE_firms_all_patents_cleaned_aggregated_NO_MANUAL_2010_2013.csv",
                 "ASIE_firms_all_patents_cleaned_aggregated_14years_NO_MANUAL_2010_2013.csv"),
}
variant = sys.argv[1] if len(sys.argv) > 1 else "all"
print(f"Patent variant: {variant}")

# Get the script directory
script_dir = Path(__file__).parent
outputs_dir = script_dir / "outputs"
inputs_dir = script_dir / "inputs"

# Load the cleaned firms data
firms_analysis = pd.read_csv(inputs_dir / "unique_name_id_year_firms_cleaned.csv")

# Filter to firms with max_consecutive_years equal to the threshold
firms_14_years = firms_analysis[firms_analysis['max_consecutive_years'] == CONSECUTIVE_YEARS_THRESHOLD]

# Get the set of firm codes (组织机构代码) with 14 consecutive years
firms_14_years_codes = set(firms_14_years['组织机构代码'].astype(str))

# Now filter patent data for 14-year firms FIRST
patent_file, patent_output_name = PATENT_VARIANTS[variant]
patent_data = pd.read_csv(inputs_dir / patent_file)

# Filter patent data to only include firms with 14 consecutive years
patent_data_14years = patent_data[patent_data['asie_id'].astype(str).isin(firms_14_years_codes)]

# Get the set of firm codes that actually appear in the patent data
firms_in_patents = set(patent_data_14years['asie_id'].dropna().astype(str).unique())

# Save the filtered patent data
patent_data_14years.to_csv(outputs_dir / patent_output_name, index=False)
print(f"{len(firms_14_years_codes):,} firms with {CONSECUTIVE_YEARS_THRESHOLD} consecutive years; "
      f"{len(firms_in_patents):,} of them have patents")
print(f"Saved {patent_output_name}: {len(patent_data_14years):,} firm-year patent records")

# Now get addresses ONLY for firms that appear in the patent data
# Load ASIE 2013 data: firms_2013_data.csv (from script 1) holds the 2013 rows of the 14-year firms only,
# which are the only firms looked up here
asie_2013 = pd.read_csv(inputs_dir / "firms_2013_data.csv")

# Filter to only the firms that are in the patent data, keeping the address columns
address_columns = ['组织机构代码', '企业名称', '省自治区直辖市', '地区市州盟', '县区市旗', '详细地址']
output_data = asie_2013.loc[asie_2013['组织机构代码'].astype(str).isin(firms_in_patents), address_columns]

# Save the address output
address_output_file = outputs_dir / "SIPO_14yearfirms.csv"
output_data.to_csv(address_output_file, index=False)
print(f"Saved {address_output_file.name}: {len(output_data):,} firm addresses")
