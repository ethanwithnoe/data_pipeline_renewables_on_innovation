import csv
import os

# Skip later rows of a patent that already produced an exact match. Off: a patent matched to several firms
# counts once for each of them, as in He et al. (2018). Setting it to True changes the patent counts.
SKIP_ALREADY_MATCHED_PATENTS = False

# File paths
script_dir = os.path.dirname(os.path.abspath(__file__))
input_file = os.path.join(script_dir, 'inputs', 'matched_firms_patents_2010_2013_FINALMULTI.csv')
output_file = os.path.join(script_dir, 'outputs', 'EXACT_matched_firms_patents.csv')
output_check_file = os.path.join(script_dir, 'outputs', 'matched_firms_patents_2010_2013_FINALMULTICHECK.csv')
name_pairs_file = os.path.join(script_dir, 'outputs', 'name_pair_unique14-5.csv')


def is_exact_match(firm_fullname, assignee_fullname_single):
    """
    Check if firm_fullname exactly matches or is a left-aligned substring of the single assignee name.
    """
    if not firm_fullname or not assignee_fullname_single:
        return False
    return assignee_fullname_single.startswith(firm_fullname)


# Track statistics
total_rows_read = 0
exact_matches_written = 0
matched_patents_set = set()  # Track which patents have been matched
unique_firms_matched = set()
non_match_name_pairs = set()  # Track unique (firm_fullname, assignee_fullname) pairs for non-matches

# Read input and write exact matches
with open(input_file, 'r', encoding='utf-8') as infile, \
     open(output_file, 'w', encoding='utf-8', newline='') as outfile, \
     open(output_check_file, 'w', encoding='utf-8', newline='') as checkfile:
    reader = csv.DictReader(infile)

    # Drop the empty 'Unnamed: ...' column carried over from the patent file
    fieldnames = [f for f in reader.fieldnames if not f.startswith('Unnamed:')]

    # Add new columns after 'assignee_fullname_single'
    check_fieldnames = list(fieldnames)
    insert_index = check_fieldnames.index('assignee_fullname_single') + 1
    check_fieldnames[insert_index:insert_index] = ['manual_check', 'true_match']

    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()

    check_writer = csv.DictWriter(checkfile, fieldnames=check_fieldnames)
    check_writer.writeheader()

    for row in reader:
        total_rows_read += 1
        row = {k: v for k, v in row.items() if not k.startswith('Unnamed:')}

        firm_fullname = row.get('firm_fullname', '').strip()
        assignee_fullname_single = row.get('assignee_fullname_single', '').strip()
        patent_number = row.get('申请号', '').strip()
        firm_id = row.get('组织机构代码', '').strip()

        # Check if this patent has already been matched
        if SKIP_ALREADY_MATCHED_PATENTS and patent_number in matched_patents_set:
            continue

        # Check for exact match
        is_match = is_exact_match(firm_fullname, assignee_fullname_single)

        # Create check row with new columns
        check_row = dict(row)
        check_row['manual_check'] = 0 if is_match else 1
        check_row['true_match'] = 'Yes'
        check_writer.writerow(check_row)

        if is_match:
            writer.writerow(row)
            exact_matches_written += 1
            matched_patents_set.add(patent_number)
            if firm_id:
                unique_firms_matched.add(firm_id)
        else:
            # Track unique (firm_fullname, assignee_fullname_single) pairs for non-matches
            non_match_name_pairs.add((firm_fullname, assignee_fullname_single))

print(f"Read {total_rows_read:,} matched rows: {exact_matches_written:,} exact matches "
      f"({len(unique_firms_matched):,} firms), {total_rows_read - exact_matches_written:,} flagged for manual check")
print(f"Saved {os.path.basename(output_file)} and {os.path.basename(output_check_file)}")

# Save unique name pairs to CSV
with open(name_pairs_file, 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['firm_fullname', 'assignee_fullname_single'])
    for firm_fullname, assignee_fullname_single in sorted(non_match_name_pairs):
        writer.writerow([firm_fullname, assignee_fullname_single])

print(f"Saved {os.path.basename(name_pairs_file)} ({len(non_match_name_pairs):,} unique non-matching name pairs)")
