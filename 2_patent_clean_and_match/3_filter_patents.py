import os
import pandas as pd

# Input and output file paths
_HERE = os.path.dirname(os.path.abspath(__file__))
input_file = os.path.join(_HERE, "inputs", "patent_db_1985_2025.csv")
output_file = os.path.join(_HERE, "outputs", "filtered_patents_2010_2013new.csv")

# Filter criteria
year_min = 2010
year_max = 2013

# Company type keywords to search for in 申请人
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

# Process in chunks to handle the large file
chunk_size = 50000  # Adjust based on your available RAM
first_chunk = True
total_filtered = 0

print(f"Filtering {os.path.basename(input_file)} to company applicants in {year_min}-{year_max} "
      f"(chunks of {chunk_size:,} rows)...")

# Read and process the file in chunks
for chunk_num, chunk in enumerate(pd.read_csv(input_file,
                                              encoding='utf-8',
                                              chunksize=chunk_size,
                                              on_bad_lines='skip',
                                              low_memory=False), 1):

    # Filter by year
    chunk = chunk[(chunk['申请年份'] >= year_min) & (chunk['申请年份'] <= year_max)]

    # Filter by company keywords (check if any keyword is in 申请人); a missing applicant matches nothing
    if len(chunk) > 0:
        mask = chunk['申请人'].fillna('').astype(str).apply(lambda x: any(keyword in x for keyword in company_keywords))
        chunk = chunk[mask]

    # Write to output file
    if len(chunk) > 0:
        chunk.to_csv(output_file,
                     mode='w' if first_chunk else 'a',
                     header=first_chunk,
                     index=False,
                     encoding='utf-8')
        first_chunk = False
        total_filtered += len(chunk)

    # Progress update
    if chunk_num % 10 == 0:
        print(f"Processed chunk {chunk_num} ({chunk_num * chunk_size:,} rows) - Found {total_filtered:,} matching rows so far...")

print(f"Saved {os.path.basename(output_file)}: {total_filtered:,} rows")
