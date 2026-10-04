import csv
import os
from collections import defaultdict
_HERE = os.path.dirname(os.path.abspath(__file__))


def aggregate_patents_by_asie_firm_year(input_filepath: str, output_filepath: str,
                                        exclude_multi_assignee: bool = False,
                                        exclude_own_manual_2010_2013: bool = False):
    """
    Count patents by ASIE firm and year, with patent types as columns.
    Each row is a firm-year with separate columns for invention, utility and design patent counts.
    False matches are already removed by 10_remove_false_matches_schools_renewables.py.

    Args:
        input_filepath: Path to input CSV file
        output_filepath: Path to output CSV file
        exclude_multi_assignee: If True, only include rows where assignee has no semicolons (single assignee)
        exclude_own_manual_2010_2013: If True, drop only the 2010-2013 manual matches
            (manual_check == '1', tagged by 7_extract_exact_matches) and keep ALL He et al. (2018) rows
            (years 1998-2009), including He's own manual_check=1 rows (the NOMANUAL variant)
    """
    keep_cols = [  # asie_id is not listed here, so it is not overwritten
        'fullname','stemname',
        'assignee', 'assignee_full', 'assignee_stem',
        '申请专利权人', '地址', '国省代码'
    ]

    # Dictionary to store counts by patent type for each firm-year
    patent_counts = defaultdict(lambda: {'i': 0, 'u': 0, 'd': 0})
    representatives = {}
    total_rows = true_match_rows = 0

    with open(input_filepath, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            total_rows += 1
            manual_check = row.get('manual_check', '')
            year_val = row.get('year', '')

            # Skip own 2010-2013 manual matches only
            if exclude_own_manual_2010_2013 and manual_check == '1' and year_val and 2010 <= int(float(year_val)) <= 2013:
                continue

            # Skip if multi-assignee filtering is enabled and assignee contains semicolons
            if exclude_multi_assignee and ';' in row.get('assignee', ''):
                continue

            true_match_rows += 1

            # Create grouping key with year as int
            key = (row.get('asie_id', ''), int(float(year_val)) if year_val else '')

            # Increment count for this patent type
            patent_type = row.get('patent_type', '')
            if patent_type in patent_counts[key]:
                patent_counts[key][patent_type] += 1

            # Store representative for keep_cols only (first occurrence)
            if key not in representatives:
                representatives[key] = {k: row.get(k, '') for k in keep_cols}

    # Build output with patent types as columns
    out_cols = ['asie_id', 'year'] + keep_cols + ['invention_patents', 'utility_patents', 'design_patents', 'total_patents']
    rows = []
    for (asie_id, year_val), counts in patent_counts.items():
        row = {'asie_id': asie_id, 'year': year_val}
        row.update(representatives[(asie_id, year_val)])  # Add other columns
        row['invention_patents'] = counts['i']
        row['utility_patents'] = counts['u']
        row['design_patents'] = counts['d']
        row['total_patents'] = counts['i'] + counts['u'] + counts['d']
        rows.append(row)

    # Sort
    rows.sort(key=lambda d: (d['asie_id'] or '', d['year']))

    # Write
    with open(output_filepath, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=out_cols)
        writer.writeheader()
        writer.writerows(rows)

    unique_firms = len(set(row['asie_id'] for row in rows if row['asie_id']))
    print(f"{os.path.basename(output_filepath)}: {true_match_rows:,} of {total_rows:,} patents -> "
          f"{len(rows):,} firm-years, {unique_firms:,} firms "
          f"(invention {sum(row['invention_patents'] for row in rows):,}, "
          f"utility {sum(row['utility_patents'] for row in rows):,}, "
          f"design {sum(row['design_patents'] for row in rows):,})")


input_file = os.path.join(_HERE, 'inputs', 'ASIE_firms_all_patents_cleaned.csv')
outputs_dir = os.path.join(_HERE, 'outputs')

# Aggregate only patents without multiple assignees (no semicolons in assignee field)
aggregate_patents_by_asie_firm_year(input_file, os.path.join(outputs_dir, 'ASIE_firms_all_patents_cleaned_aggregated_CONVERTEDNOMULTIASSIGNEE.csv'),
                                    exclude_multi_assignee=True)

# Aggregate all patents
aggregate_patents_by_asie_firm_year(input_file, os.path.join(outputs_dir, 'ASIE_firms_all_patents_cleaned_aggregated.csv'))

# NOMANUAL: all He et al. rows kept; only the 2010-2013 manual matches dropped
aggregate_patents_by_asie_firm_year(input_file, os.path.join(outputs_dir, 'ASIE_firms_all_patents_cleaned_aggregated_NO_MANUAL_2010_2013.csv'),
                                    exclude_own_manual_2010_2013=True)
