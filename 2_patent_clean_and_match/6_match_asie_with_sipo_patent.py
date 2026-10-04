import csv
import os

# Global variable for minimum max_consecutive_years threshold
MIN_MAX_CONSECUTIVE_YEARS = 14


class TrieNode:
    """Node in a Trie data structure for efficient prefix matching."""
    def __init__(self):
        self.children = {}  # Maps character -> TrieNode
        self.firm_name = None  # The firm name that ends at this node, if any


class FirmNameTrie:
    """
    Trie (prefix tree) for efficient left-aligned firm name matching.
    Optimized for finding the firm names that are prefixes of a given assignee name.
    """
    def __init__(self):
        self.root = TrieNode()

    def insert(self, firm_name):
        """Insert a firm name into the Trie."""
        node = self.root
        for char in firm_name:
            node = node.children.setdefault(char, TrieNode())
        node.firm_name = firm_name

    def find_longest_prefix(self, assignee_name):
        """Return the longest firm name in the Trie that is a prefix of assignee_name, or None."""
        longest = None
        node = self.root

        # Traverse the Trie following the assignee_name characters
        for char in assignee_name:
            if char not in node.children:
                break  # No more prefixes possible
            node = node.children[char]

            # If this node marks the end of a firm name, it is the longest so far
            if node.firm_name is not None:
                longest = node.firm_name

        return longest


# File paths
script_dir = os.path.dirname(os.path.abspath(__file__))
firms_file = os.path.join(script_dir, 'inputs', 'unique_name_id_year_firms_cleaned.csv')
patents_file = os.path.join(script_dir, 'inputs', 'filtered_patents_2010_2013_cleaned.csv')
output_file = os.path.join(script_dir, 'outputs', 'matched_firms_patents_2010_2013_FINALMULTI.csv')
firm_names_list_file = os.path.join(script_dir, 'outputs', 'firm_names_list.csv')

# Load firms data (only those meeting the threshold)
firms_to_match = []
with open(firms_file, 'r', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        max_consecutive = int(row.get('max_consecutive_years', 0))

        # Stop when below threshold (since sorted from most to least)
        if max_consecutive < MIN_MAX_CONSECUTIVE_YEARS:
            break

        firms_to_match.append({
            '组织机构代码': row.get('组织机构代码', ''),
            '企业名称': row.get('企业名称', ''),
            'firm_fullname': row.get('firm_fullname', ''),
            'max_consecutive_years': max_consecutive
        })

# Create a Trie of unique firm names
unique_firm_names = list(set(firm['企业名称'] for firm in firms_to_match))
print(f"Matching {len(unique_firm_names):,} names of the {len(firms_to_match):,} firm-name rows with "
      f"max_consecutive_years >= {MIN_MAX_CONSECUTIVE_YEARS} against the 2010-2013 patents...")

firm_name_trie = FirmNameTrie()
for name in unique_firm_names:
    if name:
        firm_name_trie.insert(name)

# Save firm_names_list to CSV (for reference)
with open(firm_names_list_file, 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['firm_name', 'length'])
    for name in sorted(unique_firm_names, key=lambda x: (-len(x), x)):
        writer.writerow([name, len(name)])

# Map each firm name to the latest (last) firm variant with this name
latest_firm_by_name = {firm['企业名称']: firm for firm in firms_to_match}

# Perform left-aligned matching
total_matches = 0
patents_processed = 0
matched_patents_with_multiple_assignees = set()  # Track unique matched patents with multiple assignees

with open(patents_file, 'r', encoding='utf-8') as patents_f, \
     open(output_file, 'w', encoding='utf-8', newline='') as outfile:
    patent_reader = csv.DictReader(patents_f)
    patent_fieldnames = patent_reader.fieldnames

    # Define output columns: firm columns first, then all patent columns,
    # with assignee_fullname_single inserted after assignee_fullname
    firm_columns = ['组织机构代码', '企业名称', 'firm_fullname', 'max_consecutive_years']
    assignee_fullname_idx = patent_fieldnames.index('assignee_fullname')
    fieldnames = (firm_columns + patent_fieldnames[:assignee_fullname_idx+1] + ['assignee_fullname_single']
                  + patent_fieldnames[assignee_fullname_idx+1:])

    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()

    for patent in patent_reader:
        assignee_name = patent.get('申请人', '')
        assignee_fullname = patent.get('assignee_fullname', '')
        patent_id = patent.get('申请号', '') or patent.get('公开号', '') or str(patents_processed)  # Use application number or publication number as unique ID
        patents_processed += 1

        # Split assignee name by semicolons and check each one
        assignee_names = [name.strip() for name in assignee_name.split(';')]
        assignee_fullnames = [name.strip() for name in assignee_fullname.split(';')] if assignee_fullname else assignee_names
        patent_matched = False  # Track if this patent produces any match

        for idx, single_assignee in enumerate(assignee_names):
            if not single_assignee:
                continue

            # Take only the longest firm name that is a left-aligned prefix of this assignee
            firm_name = firm_name_trie.find_longest_prefix(single_assignee)
            if firm_name is None:
                continue

            # Write only the latest (last) firm variant with this name
            latest_firm = latest_firm_by_name[firm_name]
            match_row = dict(latest_firm)
            # Add all patent columns
            match_row.update(patent)
            # Override with only the matched assignee name (AFTER update to avoid being overwritten)
            match_row['申请人'] = single_assignee
            match_row['assignee_fullname_single'] = assignee_fullnames[idx] if idx < len(assignee_fullnames) else single_assignee

            writer.writerow(match_row)
            total_matches += 1
            patent_matched = True

        # Track if this matched patent has multiple assignees (count each patent only once)
        if patent_matched and len(assignee_names) > 1:
            matched_patents_with_multiple_assignees.add(patent_id)

print(f"Processed {patents_processed:,} patents: {total_matches:,} matches "
      f"({len(matched_patents_with_multiple_assignees):,} matched patents have multiple assignees)")
print(f"Saved {os.path.basename(output_file)} and {os.path.basename(firm_names_list_file)}")
