# Data Pipeline: The Effect of Opening Renewable Energy Firms on Local Innovation in China

This repo contains the data pipeline to build the dataset for the paper using ASIE firm data, CNIPA patents and Gaode coordinates. It also contains the Stata code (`stata_code`) as well as the figures and tables used in the paper (`figures_and_tables`).

## Setup

```
python -m pip install -r requirements.txt     # installs Python requirements
python run_pipeline.py --setup-folders        # creates the inputs/ and outputs/ folders
```

## Running

```
python run_pipeline.py                      # all scripts from raw data
python run_pipeline.py --stages 5-7         # some stages (can run after a full run through)
python run_pipeline.py --scripts 19         # a single script (can run after a full run through)
python run_pipeline.py --from-intermediate  # start from given files (see below)
```

The runner copies each stage's inputs from the earlier outputs. By default both `--filter-patents`, which
rebuilds the patent file from the raw SIPO database, and `--geocode` which calls the paid Gaode API, are not run. 

Without the raw ASIE and patent data, use `--from-intermediate` (see below).

| Stage | Scripts | What it Does |
|---|---|---|
| 1 | 1, 2 | Creates balanced panel of firms from ASIE data |
| 2 | 3–8 | Cleans names and matches 2010–2013 CNIPA patents to firms |
| 3 | 9–11 | Combines 2010-2013 data with He et al. (2018) data, removes school linked patents, and creates patent counts |
| 4 | 12 | Keeps the 14-year firms with patents and saves their addresses |
| 5 | 13–16 | Cleans and formats addresses for Gaode Maps API, Runs Gaode API, calculates distances between plants and firms within 50 km |
| 6 | 18 | Create one time-invariant industry code per firm |
| 7 | 19 | Combine all previous data to create four final datasets |
| 8 | 21 | Generates the three maps for paper |

## Outputs

`7_final_combine/outputs/`:
- **`firm_patent_renewable50KM.csv`**: the baseline panel;
- **`firm_patent_NOMULTIASSIGNEE50KM.csv`**: only single-assignee patents;
- **`firm_patent_NOMANUAL50KM.csv`**: excludes manually checked 2010–2013 matches;
- **`firm_patent_PLACEBO50KM.csv`**: placebo test for renewables.

`8_mapping_figures/outputs/` holds the three maps. 

## Data

Due to both size (the full raw data is 100+ GB) and data licensing/privacy restrictions, the full dataset cannot be included in this repo. This includes the following:
- ASIE 2000–2013 data, needed for Scripts 1 and 2 in Stage 1
- the full CNIPA patent file, needed for Script 3 in Stage 2
- the He et al. (2018) 1998-2009 firm-patent matched data, needed for Script 9 in Stage 3

The Gaode API key cannot be shared as it is a paid API key.

However, I have included the following intermediate data sources in a Google Drive link attached in the application.

In order to run the pipeline with the intermediate files, place them like so.

| File in the Drive folder | Put at |
|---|---|
| `unique_name_id_year_14year_firms.csv` | `2_patent_clean_and_match/inputs/unique_name_id_year_firms.csv` | 
| `firm_characteristics_14year_firms.csv` | `6_industry_code_conversion/inputs/firm_characteristics_by_year_firm_code.csv` |
| `firms_2013_data.csv` | `4_filter_14yr_and_addresses/inputs/firms_2013_data.csv` | 
| `matched_firms_patents_2010_2013_CONVERTEDNODUPES.csv` | `3_merge_and_clean_patents/inputs/SIPO_patents/` | 
| `ASIE_Renewables_Firms_2000-2013.csv`, `ASIE_NONrenewableFirms2000-2013.csv` | `5_geolocating/inputs/` | 
| `geo_SIPO_14yearfirms_full_address.json`, `geo_Realrenewable_firmsMC_full_address.json`, `geo_NonRenewable2013NamesFilled_cleaned_full_address.json` | `5_geolocating/inputs/` |
| `geo_SIPO_14yearfirms_full_address_FINAL.csv`, `geo_Realrenewable_firmsMC_full_address_addresses.csv` | `5_geolocating/inputs/` |
| `ne_10m_admin_1_states_provinces.zip` | `8_mapping_figures/map_source/` |

For the He et al. (2018) firm-patent data, download the three files `ASIE firms matched to design patents.txt`,
`… invention patents.txt` and `… utility model patents.txt` [here](https://sites.google.com/site/sipopdb/cpdp-home/sipo-asie-firms?authuser=0) or [here](https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/QUH8KT) 

Place them into `3_merge_and_clean_patents/inputs/SIPO_patents/`. (Make sure to convert to `.csv` and insure they are comma seperated before using them)

Then run `python run_pipeline.py --from-intermediate`

## Stata Files
Under `stata_code` are four files which do the following:

| Name of Code | Output |
|---|---|
| `filter_NONrenewable_firms.do` | Creates a `.csv` file with only nonrenewables |
| `filter_renewable_firms.do`| Creates a `.csv` file with only renewables and the graph of openings by year |
| `firm_year_regression_robust.do` | Runs regressions on the baseline as well as robustness checks (including the placebo test) |
| `event_study_utility_patent.do` | Runs event study on utility patents |

**Note that `filter_NONrenewable_firms.do` and `filter_renewable_firms.do` can not be run without the original ASIE data**

Also install the Stata packages `reghdfe`, `ftools`, `estout` and `eventdd`