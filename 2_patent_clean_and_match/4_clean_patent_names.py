import csv
import re
import os

# Company type keywords to remove from end of firm names
company_keywords = [
    '股份有限责任公司',
    '股份有限公司',
    '有限责任公司',
    '独立行政法人',
    '有限总公司',
    '有限分公司',
    '总公司',
    '分公司',
    '董事会',
    '集团',
    '有限公司',
    '有限责任',
    '株式会社',
    '公司',
    '股份',
    '企业',
    '工厂',
    '厂'
]
# Sort by length (longest first) to match longer suffixes first
company_keywords_longest_first = sorted(company_keywords, key=len, reverse=True)

educational_keywords = ['大学', '学院', '学校', '中学', '小学']

# Mapping of Arabic digits to Chinese numbers
digit_map = str.maketrans('0123456789', '零一二三四五六七八九')


def remove_company_suffix(name):
    """Remove company type suffixes from the end of firm name."""
    if not isinstance(name, str):
        return name

    # Try to remove one suffix from the end
    for suffix in company_keywords_longest_first:
        if name.endswith(suffix):
            return name[:-len(suffix)].strip()

    return name


def clean_firm_name(name):
    """
    Clean firm name by removing all symbols and punctuation marks
    while keeping letters, characters (including Chinese), and numbers.
    Content inside parentheses is kept, only the parentheses themselves are removed.
    Converts full-width alphanumeric characters to half-width.
    Converts Arabic numbers to Chinese numbers.
    """
    if not name or name.strip() == '':
        return name

    name = str(name)

    # Convert full-width alphanumeric to half-width
    # Full-width: Ａ-Ｚ (U+FF21-FF3A), ａ-ｚ (U+FF41-FF5A), ０-９ (U+FF10-FF19)
    # Offset is 0xFEE0 between full-width and half-width
    converted = []
    for char in name:
        code = ord(char)
        if 0xFF21 <= code <= 0xFF3A or 0xFF41 <= code <= 0xFF5A or 0xFF10 <= code <= 0xFF19:
            converted.append(chr(code - 0xFEE0))
        else:
            converted.append(char)
    name = ''.join(converted)

    # Convert Arabic numbers to Chinese numbers
    name = name.translate(digit_map)

    # Remove all symbols, punctuation and whitespace
    # Keep only: Chinese characters and letters (a-zA-Z) and digits (0-9)
    return re.sub(r'[^\u4e00-\u9fff\u3400-\u4dbf\uac00-\ud7afa-zA-Z0-9]', '', name)


def clean_assignee_names(names):
    """
    Clean assignee names by applying cleaning to each name separated by semicolons.
    Preserves semicolon separators between multiple assignees.
    Does NOT remove company suffixes.
    """
    if not names or names.strip() == '':
        return names

    # Convert full-width semicolons to half-width, then clean each name and rejoin
    names = names.replace('；', ';')
    return ';'.join(clean_firm_name(assignee) for assignee in names.split(';'))


def remove_assignee_suffix(names):
    """
    Remove company suffixes from assignee names separated by semicolons.
    """
    if not names or names.strip() == '':
        return names

    return ';'.join(remove_company_suffix(assignee) for assignee in names.split(';'))


def is_educational_institution(assignee_fullname):
    """
    Check if any assignee name ends with educational institution keywords.
    Returns True if any assignee ends with: 大学, 学院, 学校, 中学, or 小学
    Handles multiple assignees separated by semicolons.
    """
    if not assignee_fullname or assignee_fullname.strip() == '':
        return False

    return any(assignee.strip().endswith(keyword)
               for assignee in assignee_fullname.split(';')
               for keyword in educational_keywords)


# Configuration: Toggle to exclude educational institutions
EXCLUDE_EDUCATIONAL_INSTITUTIONS = True  # Set to False to keep educational institutions

# File paths
script_dir = os.path.dirname(os.path.abspath(__file__))
input_file = os.path.join(script_dir, 'inputs', 'filtered_patents_2010_2013.csv')
output_file = os.path.join(script_dir, 'outputs', 'filtered_patents_2010_2013_cleaned.csv')

row_count = 0
excluded_count = 0
duplicate_count = 0
seen_application_numbers = set()

# Process CSV line by line
with open(input_file, 'r', encoding='utf-8') as infile, \
     open(output_file, 'w', encoding='utf-8', newline='') as outfile:

    reader = csv.DictReader(infile)
    original_fieldnames = list(reader.fieldnames)

    # Insert 'assignee_fullname' right after '申请人'
    assignee_idx = original_fieldnames.index('申请人')
    new_fieldnames = original_fieldnames[:assignee_idx+1] + ['assignee_fullname'] + original_fieldnames[assignee_idx+1:]

    writer = csv.DictWriter(outfile, fieldnames=new_fieldnames)
    writer.writeheader()

    for row in reader:
        row_count += 1

        # Clean the assignee name(s) - handles multiple assignees separated by semicolons
        cleaned_names = clean_assignee_names(row['申请人'])

        # Store cleaned name (without suffix removal) in assignee_fullname
        row['assignee_fullname'] = cleaned_names

        # Remove company suffix for 申请人
        row['申请人'] = remove_assignee_suffix(cleaned_names)

        # Check if we should exclude educational institutions
        if EXCLUDE_EDUCATIONAL_INSTITUTIONS and is_educational_institution(cleaned_names):
            excluded_count += 1
            continue

        # Check for duplicate patent using 申请号 (keep the first instance)
        app_number = (row.get('申请号') or '').strip()
        if app_number:
            if app_number in seen_application_numbers:
                duplicate_count += 1
                continue
            seen_application_numbers.add(app_number)

        # Write cleaned row
        writer.writerow(row)

print(f"Cleaned {row_count:,} patents: {excluded_count:,} educational institutions and {duplicate_count:,} "
      f"duplicate application numbers removed; {row_count - excluded_count - duplicate_count:,} rows saved to "
      f"{os.path.basename(output_file)}")
