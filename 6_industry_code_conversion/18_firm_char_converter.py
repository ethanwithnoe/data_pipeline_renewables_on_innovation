import pandas as pd
import os
_HERE = os.path.dirname(os.path.abspath(__file__))


def assign_modal_industry_code(data_file=os.path.join(_HERE, 'inputs', 'firm_characteristics_by_year_firm_code.csv')):
    """
    Save ALL years for 14+ year firms, with one time-invariant industry code per firm (the modal code).
    """
    df = pd.read_csv(data_file)

    # Identify firms with 14+ consecutive years and keep ALL rows for these firms only
    firm_max_years = df.groupby('firm_id')['max_consecutive_years'].max()
    long_firm_ids = firm_max_years[firm_max_years >= 14].index.tolist()
    result = df[df['firm_id'].isin(long_firm_ids)].copy()

    # One time-invariant industry code per firm = the code the firm reports most often over 2000-2013.
    # The raw code switches classification system (GB/T 1994 in 2000-02, GB/T 2002 in 2003-12, GB/T 2011 in 2013),
    # so it changes for most firms at those seams. The mode is always a GB/T 2002 code in this sample (10 of
    # 14 years). Ties -> the tied code used most recently in 2003-2012 (then most recently overall). The
    # year-varying original is kept as firm_code_raw.
    result['firm_code_raw'] = result['firm_code']
    codes = result[['firm_id', 'year']].assign(code=pd.to_numeric(result['firm_code'], errors='coerce')).dropna(subset=['code'])
    codes['year_mid'] = codes['year'].where(codes['year'].between(2003, 2012), -1)
    code_stats = codes.groupby(['firm_id', 'code']).agg(n=('year', 'size'), last_mid=('year_mid', 'max'),
                                                       last_any=('year', 'max')).reset_index()
    code_stats = code_stats.sort_values(['firm_id', 'n', 'last_mid', 'last_any'], ascending=[True, False, False, False])
    modal_code = code_stats.drop_duplicates('firm_id').set_index('firm_id')['code']
    result['firm_code'] = result['firm_id'].map(modal_code)
    print(f"firm_code = modal code per firm; firms whose raw code varies: "
          f"{int((result.groupby('firm_id')['firm_code_raw'].nunique() > 1).sum()):,}")

    # Sort by firm_id, year and save
    result = result.sort_values(['firm_id', 'year']).reset_index(drop=True)
    output_file = os.path.join(_HERE, 'outputs', 'firm_14plus_years_2013_codes_converted.csv')
    result.to_csv(output_file, index=False)
    print(f"Saved {os.path.basename(output_file)}: {len(result):,} rows (all years) for "
          f"{len(long_firm_ids):,} firms with 14+ consecutive years")


if __name__ == "__main__":
    assign_modal_industry_code()
