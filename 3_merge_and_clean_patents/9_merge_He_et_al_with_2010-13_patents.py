import pandas as pd
import os
_HERE = os.path.dirname(os.path.abspath(__file__))
SIPO_DIR = os.path.join(_HERE, 'inputs', 'SIPO_patents')

# Read the three patent CSV files
design = pd.read_csv(os.path.join(SIPO_DIR, 'ASIE firms matched to design patents.csv'),
                     encoding='utf-8', low_memory=False)

invention = pd.read_csv(os.path.join(SIPO_DIR, 'ASIE firms matched to invention patents.csv'),
                        encoding='utf-8', low_memory=False)

utility = pd.read_csv(os.path.join(SIPO_DIR, 'ASIE firms matched to utility model patents.csv'),
                      encoding='utf-8', low_memory=False)
print(f"He et al. (2018) matched patents: {len(design):,} design, {len(invention):,} invention, "
      f"{len(utility):,} utility model")

# Add a column to identify patent type if it doesn't exist
if 'patent_type' not in design.columns:
    design['patent_type'] = 'd'  # design
if 'patent_type' not in invention.columns:
    invention['patent_type'] = 'i'  # invention
if 'patent_type' not in utility.columns:
    utility['patent_type'] = 'u'  # utility model

# Concatenate all three dataframes
all_patents = pd.concat([design, invention, utility], ignore_index=True)


# ============================================================================
# Merge in the 2010-2013 matched patents (stage 2)
# ============================================================================
def merge_with_2010_2013_converted(existing_df, converted_file_path):
    """
    Merges the 2010-2013 converted patents file with existing patents.
    If the columns differ, a warning is printed and the union of columns is kept
    (non-shared fields become NaN) instead of dropping the 2010-2013 patents.
    """
    converted_df = pd.read_csv(converted_file_path, encoding='utf-8', low_memory=False)

    # Check if columns match
    missing_in_converted = set(existing_df.columns) - set(converted_df.columns)
    extra_in_converted = set(converted_df.columns) - set(existing_df.columns)
    if missing_in_converted or extra_in_converted:
        print(f"WARNING: column mismatch. Missing in converted file: {sorted(missing_in_converted)}; "
              f"extra in converted file: {sorted(extra_in_converted)}. Concatenating the union of columns anyway.")

    # Merge the dataframes
    combined_df = pd.concat([existing_df, converted_df], ignore_index=True)
    print(f"Added {len(converted_df):,} matched 2010-2013 patents: {len(combined_df):,} records in total")
    return combined_df


all_patents = merge_with_2010_2013_converted(
    all_patents,
    os.path.join(SIPO_DIR, 'matched_firms_patents_2010_2013_CONVERTEDNODUPES.csv')
)

# Save the merged file
output_path = os.path.join(_HERE, 'outputs', 'ASIE_firms_all_patents_merged.csv')
all_patents.to_csv(output_path, index=False, encoding='utf-8')
print(f"Saved {os.path.basename(output_path)}")
