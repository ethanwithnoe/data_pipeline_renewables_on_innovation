import csv
import os

# Column mappings: (old_name, new_name)
# Only columns that exist in the source will be included
COLUMN_MAPPINGS = [
    ('组织机构代码', 'asie_id'),
    ('firm_fullname', 'fullname'),
    ('企业名称', 'stemname'),
    ('专利类型', 'patent_type'),
    ('申请年份', 'year'),
    ('申请人', 'assignee_stem'),
    ('assignee_fullname', 'assignee'),
    ('assignee_fullname_single', 'assignee_full'),
    ('manual_check', 'manual_check'),
    ('true_match', 'true_match'),
    ('公开公告日', '公开公告日'),
    ('申请日', '申请日'),
    ('IPC主分类号', '主分类号'),
    ('IPC分类号', '分类号'),
    ('申请人地址', '地址'),
    ('申请号', '申请号'),
    ('公开公告号', '公开号'),
]

# Value conversions for specific columns
# Format: column_name -> {old_value: new_value}
VALUE_CONVERSIONS = {
    'patent_type': {
        '实用新型': 'u',
        '发明授权': 'i',
        '发明申请': 'i',
        '外观设计': 'd',
    }
}

# Desired output column order
# Include all columns from COLUMNS_ORDER, even if they don't exist in source
COLUMNS_ORDER = [
    'asie_id',
    'fullname',
    'stemname',
    'patent_type',
    'serial_no',
    'year',
    'assignee',
    'assignee_full',
    'assignee_stem',
    'manual_check',
    'true_match',
    '公开公告日',
    '申请日',
    '主分类号',
    '分类号',
    '分案原申请号',
    '优先权',
    '申请专利权人',
    '地址',
    '专利代理机构',
    '代理人',
    '页数',
    '国省代码',
    '申请号',
    '公开号',
]

# File paths
script_dir = os.path.dirname(os.path.abspath(__file__))
input_file = os.path.join(script_dir, 'inputs', 'matched_firms_patents_2010_2013_FINALMULTICHECK.csv')
output_file = os.path.join(script_dir, 'outputs', 'matched_firms_patents_2010_2013_CONVERTEDNODUPES.csv')

# Create mapping dictionary
column_map = dict(COLUMN_MAPPINGS)

# First, read and convert all rows
all_rows = []
with open(input_file, 'r', encoding='utf-8') as infile:
    for row in csv.DictReader(infile):
        # Convert row to new column names
        new_row = {}
        for old_name, value in row.items():
            new_name = column_map.get(old_name, old_name)
            # Only include if in output columns
            if new_name in COLUMNS_ORDER:
                # Apply value conversions if defined for this column
                value = VALUE_CONVERSIONS.get(new_name, {}).get(value, value)
                # Convert year to int
                if new_name == 'year' and value:
                    value = int(float(value))
                new_row[new_name] = value
        all_rows.append(new_row)

# Sort by asie_id
all_rows.sort(key=lambda x: x.get('asie_id', ''))

# Write sorted data
with open(output_file, 'w', encoding='utf-8', newline='') as outfile:
    writer = csv.DictWriter(outfile, fieldnames=COLUMNS_ORDER)
    writer.writeheader()
    writer.writerows(all_rows)

print(f"Converted {len(all_rows):,} rows to the He et al. column layout; saved {os.path.basename(output_file)}")
