import csv
import os
_HERE = os.path.dirname(os.path.abspath(__file__))


def filter_true_matches_only(rows):
    """
    Remove all false matches (true_match = 'No' or 'no') and educational institutions.
    Educational institutions are identified if any applicant name ends with:
    大学, 学院, 学校, 中学, 小学
    """
    educational_keywords = ('大学', '学院', '学校', '中学', '小学')
    kept = []
    total_count = 0
    educational_filtered = 0
    before_2000_filtered = 0

    for row in rows:
        total_count += 1
        # Skip false matches
        if row.get('true_match', '').strip().lower() == 'no':
            continue
        year = row.get('year', '').strip()
        if year.lower() == 'no':
            continue

        # Skip years before 2000
        try:
            # Convert to float first (handles '2005.0'), then to int
            if int(float(year)) < 2000:
                before_2000_filtered += 1
                continue
        except ValueError:
            pass  # Keep rows with invalid year values

        # Check if any applicant is an educational institution
        applicants = [a.strip() for a in row.get('assignee', '').split(';')]
        if any(applicant.endswith(educational_keywords) for applicant in applicants if applicant):
            educational_filtered += 1
            continue

        # Keep only non-educational true matches
        kept.append(row)

    print(f"Filtered {total_count:,} rows: removed {total_count - len(kept) - educational_filtered - before_2000_filtered:,} "
          f"false matches, {educational_filtered:,} educational institutions, {before_2000_filtered:,} pre-2000 patents; "
          f"kept {len(kept):,}")
    return kept


def remove_renewables(rows):
    # Use the organization codes of the renewable-energy equipment makers
    with open(os.path.join(_HERE, 'inputs', 'ASIE_Renewables_Firms_2000-2013.csv'), 'r', encoding='utf-8') as f:
        asie_ids_to_remove = {row['组织机构代码'].strip() for row in csv.DictReader(f)} - {''}

    # Remove if asie_id matches any of the organization codes
    kept = [row for row in rows if row.get('asie_id', '').strip() not in asie_ids_to_remove]
    print(f"Removed {len(rows) - len(kept):,} patents of the "
          f"{len(asie_ids_to_remove):,} renewable-energy equipment makers; {len(kept):,} kept")
    return kept


def remove_duplicates_by_application_and_firm(rows):
    """
    Removes duplicate patents based on 申请号 (application number) and asie_id.

    Deduplication logic:
    - A duplicate is when both 申请号 and asie_id are identical
    - Priority 1: Remove rows with manual_check = 1 (non-exact matches)
    - Priority 2: If manual_check is the same, keep first encountered row
    """
    # Store: {(申请号, asie_id): (row_index, manual_check_value, row_dict)}
    best_rows = {}
    duplicate_years_2000_2009 = 0
    duplicate_years_2010_2013 = 0

    for row_idx, row in enumerate(rows):
        key = (row['申请号'], row['asie_id'])
        try:
            manual_check = int(row.get('manual_check', 0))
        except (ValueError, TypeError):
            manual_check = 0

        if key not in best_rows:
            # First time seeing this combination
            best_rows[key] = (row_idx, manual_check, row)
            continue

        # We've seen this combination before - this is a duplicate
        # Prioritize: lower manual_check wins (0 before 1); if tie, keep the earlier row
        existing_idx, existing_manual_check, existing_row = best_rows[key]
        should_replace = manual_check < existing_manual_check

        # Track year range of the duplicate being REMOVED
        discarded_row = existing_row if should_replace else row
        try:
            # Convert to float first (handles '2005.0'), then to int
            discard_year = int(float(discarded_row.get('year', '')))
            if 2000 <= discard_year <= 2009:
                duplicate_years_2000_2009 += 1
            elif 2010 <= discard_year <= 2013:
                duplicate_years_2010_2013 += 1
        except (ValueError, TypeError):
            pass

        if should_replace:
            best_rows[key] = (row_idx, manual_check, row)

    rows_to_keep = {idx for idx, _, _ in best_rows.values()}
    kept = [row for row_idx, row in enumerate(rows) if row_idx in rows_to_keep]
    print(f"Removed {len(rows) - len(kept):,} duplicate (申请号, asie_id) rows "
          f"({duplicate_years_2000_2009:,} from 2000-2009, {duplicate_years_2010_2013:,} from 2010-2013)")
    return kept


input_file = os.path.join(_HERE, 'inputs', 'ASIE_firms_all_patents_merged.csv')
output_file = os.path.join(_HERE, 'outputs', 'ASIE_firms_all_patents_cleaned.csv')

with open(input_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    rows = filter_true_matches_only(reader)

# Sort by asie_id, then year, then application date
rows.sort(key=lambda x: (x.get('asie_id', ''), x.get('year', ''), x.get('申请日', '')))
rows = remove_renewables(rows)
rows = remove_duplicates_by_application_and_firm(rows)

with open(output_file, 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
print(f"Saved {len(rows):,} rows to {os.path.basename(output_file)}")
