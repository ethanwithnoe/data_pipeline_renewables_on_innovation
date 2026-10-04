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
    name = re.sub(r'[^\u4e00-\u9fff\u3400-\u4dbf\uac00-\ud7afa-zA-Z0-9]', '', name)
    return name


# File paths
script_dir = os.path.dirname(os.path.abspath(__file__))
input_file = os.path.join(script_dir, 'inputs', 'unique_name_id_year_firms.csv')
output_file = os.path.join(script_dir, 'outputs', 'unique_name_id_year_firms_cleaned.csv')

row_count = 0

# Process CSV line by line
with open(input_file, 'r', encoding='utf-8') as infile, \
     open(output_file, 'w', encoding='utf-8', newline='') as outfile:

    reader = csv.DictReader(infile)
    original_fieldnames = list(reader.fieldnames)

    # Insert 'firm_fullname' right after '企业名称'
    firm_name_idx = original_fieldnames.index('企业名称')
    new_fieldnames = original_fieldnames[:firm_name_idx+1] + ['firm_fullname'] + original_fieldnames[firm_name_idx+1:]

    writer = csv.DictWriter(outfile, fieldnames=new_fieldnames)
    writer.writeheader()

    for row in reader:
        # Clean the firm name (without suffix removal)
        cleaned_name = clean_firm_name(row['企业名称'])

        # Store cleaned name (without suffix removal) in firm_fullname
        row['firm_fullname'] = cleaned_name

        # Remove company suffix for 企业名称
        row['企业名称'] = remove_company_suffix(cleaned_name)

        # Write cleaned row
        writer.writerow(row)
        row_count += 1

print(f"Cleaned {row_count:,} firm names; saved {os.path.basename(output_file)}")
