import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
S1, S2, S3, S4, S5, S6, S7, S8 = (ROOT / d for d in (
    "1_ASIE_firm_panel", "2_patent_clean_and_match", "3_merge_and_clean_patents", "4_filter_14yr_and_addresses",
    "5_geolocating", "6_industry_code_conversion", "7_final_combine", "8_mapping_figures"))


def I(stage, *p):
    return stage.joinpath("inputs", *p)


def O(stage, *p):
    return stage.joinpath("outputs", *p)


NEARBY_REAL = "nearby_firms_50km_geo_Realrenewable_firmsMC_full_address_addresses_vs_geo_SIPO_14yearfirms_full_address_FINALpyproj.csv"
NEARBY_PLACEBO = "nearby_firms_50km_geo_NonRenewable2013NamesFilled_cleaned_full_address_addresses_vs_geo_SIPO_14yearfirms_full_address_FINALpyproj.csv"
AGG = "ASIE_firms_all_patents_cleaned_aggregated"
RENEWABLE_LIST = "ASIE_Renewables_Firms_2000-2013.csv"   # renewable-energy equipment makers (3825/3415/3414)
PLACEBO_LIST = "ASIE_NONrenewableFirms2000-2013"          # placebo makers (3411/3412/3413), file stem
# Steps that need the raw ASIE years or the raw patent file; --from-intermediate skips them
RAW_STEPS = {"1", "2", "3", "4", "6", "7", "8"}


def step(sid, stage, script, *args, copy=(), after=(), needs=(), optional=None):
    """One script run.
    copy:  (source, destination) handoffs done before the run (earlier outputs -> this stage's inputs/)
    after: handoffs done after the run
    needs: supplied input files that must already exist (raw data, hand-completed files)
    optional: None, or the flag ('filter' / 'geocode') that switches this step on"""
    return dict(id=sid, stage=stage, script=script, args=list(args), copy=list(copy), after=list(after),
                needs=list(needs), optional=optional,
                label=f"{script} {' '.join(Path(a).name if isinstance(a, Path) else a for a in args)}".strip())


ASIE_YEARS = [I(S1, "ASIE_csv", f"ASIE_{y}.csv") for y in range(2000, 2014)]
GEO_STEMS = [  # (address file written by 13, geocode JSON name the later steps read)
    ("SIPO_14yearfirms_full_address", "geo_SIPO_14yearfirms_full_address.json"),
    ("ASIE_Renewables_Firms_2000-2013_full_address", "geo_Realrenewable_firmsMC_full_address.json"),
    (f"{PLACEBO_LIST}_full_address", "geo_NonRenewable2013NamesFilled_cleaned_full_address.json"),
]

STEPS = [
    # ---- stage 1: ASIE firm panel
    step("1", 1, "1_create_firm_characteristics.py", needs=ASIE_YEARS),
    step("2", 1, "2_find_unique_name_id.py", needs=ASIE_YEARS),

    # ---- stage 2: patent cleaning and name matching (2010-2013 patents)
    step("3", 2, "3_filter_patents.py", optional="filter", needs=[I(S2, "patent_db_1985_2025.csv")],
         after=[(O(S2, "filtered_patents_2010_2013new.csv"), I(S2, "filtered_patents_2010_2013.csv"))]),
    step("4", 2, "4_clean_patent_names.py", needs=[I(S2, "filtered_patents_2010_2013.csv")]),
    step("5", 2, "5_clean_firm_names.py",
         copy=[(O(S1, "unique_name_id_year_14year_firms.csv"), I(S2, "unique_name_id_year_firms.csv"))]),
    step("6", 2, "6_match_asie_with_sipo_patent.py",
         copy=[(O(S2, "filtered_patents_2010_2013_cleaned.csv"), I(S2, "filtered_patents_2010_2013_cleaned.csv")),
               (O(S2, "unique_name_id_year_firms_cleaned.csv"), I(S2, "unique_name_id_year_firms_cleaned.csv"))]),
    step("7", 2, "7_extract_exact_matches.py",
         copy=[(O(S2, "matched_firms_patents_2010_2013_FINALMULTI.csv"),
                I(S2, "matched_firms_patents_2010_2013_FINALMULTI.csv"))]),
    step("8", 2, "8_convert_headers.py",
         copy=[(O(S2, "matched_firms_patents_2010_2013_FINALMULTICHECK.csv"),
                I(S2, "matched_firms_patents_2010_2013_FINALMULTICHECK.csv"))]),

    # ---- stage 3: merge with He et al. (2018), clean, aggregate by invention/utility/design
    step("9", 3, "9_merge_He_et_al_with_2010-13_patents.py",
         copy=[(O(S2, "matched_firms_patents_2010_2013_CONVERTEDNODUPES.csv"),
                I(S3, "SIPO_patents", "matched_firms_patents_2010_2013_CONVERTEDNODUPES.csv"))],
         needs=[I(S3, "SIPO_patents", f"ASIE firms matched to {k} patents.csv")
                for k in ("design", "invention", "utility model")]),
    step("10", 3, "10_remove_false_matches_schools_renewables.py",
         copy=[(O(S3, "ASIE_firms_all_patents_merged.csv"), I(S3, "ASIE_firms_all_patents_merged.csv")),
               (I(S5, RENEWABLE_LIST), I(S3, RENEWABLE_LIST))]),
    step("11", 3, "11_merge_IUD_patent_category_by_firm.py",
         copy=[(O(S3, "ASIE_firms_all_patents_cleaned.csv"), I(S3, "ASIE_firms_all_patents_cleaned.csv"))]),

    # ---- stage 4: 14-year firms and their addresses. The all-patents run must be LAST: every run writes
    # SIPO_14yearfirms.csv, and the list that was geocoded is the all-patents one.
    step("12", 4, "12_check_14year_firms_in_patents.py", "nomulti",
         copy=[(O(S3, f"{AGG}.csv"), I(S4, f"{AGG}.csv")),
               (O(S3, f"{AGG}_CONVERTEDNOMULTIASSIGNEE.csv"), I(S4, f"{AGG}_CONVERTEDNOMULTIASSIGNEE.csv")),
               (O(S3, f"{AGG}_NO_MANUAL_2010_2013.csv"), I(S4, f"{AGG}_NO_MANUAL_2010_2013.csv")),
               (O(S2, "unique_name_id_year_firms_cleaned.csv"), I(S4, "unique_name_id_year_firms_cleaned.csv")),
               (O(S1, "firms_2013_data.csv"), I(S4, "firms_2013_data.csv"))]),
    step("12", 4, "12_check_14year_firms_in_patents.py", "nomanual"),
    step("12", 4, "12_check_14year_firms_in_patents.py", "all"),

    # ---- stage 5: addresses, geocoding (Gaode), distances between plants and firms
    step("13", 5, "13_make_address_from_asie.py", "input", I(S5, "SIPO_14yearfirms.csv"),
         copy=[(O(S4, "SIPO_14yearfirms.csv"), I(S5, "SIPO_14yearfirms.csv"))]),
    step("13", 5, "13_make_address_from_asie.py", "input", I(S5, RENEWABLE_LIST),
         needs=[I(S5, RENEWABLE_LIST)]),
    step("13", 5, "13_make_address_from_asie.py", "input", I(S5, f"{PLACEBO_LIST}.csv"),
         needs=[I(S5, f"{PLACEBO_LIST}.csv")]),
    *[step("14", 5, "14_gaodelocate.py", "input", O(S5, f"{stem}.csv"), optional="geocode",
           needs=[S5 / ".env"], after=[(O(S5, f"geo_{stem}.json"), I(S5, geo_json))])
      for stem, geo_json in GEO_STEMS],
    step("14a", 5, "14a_extract_failed_geocodes.py", "input", "geo_SIPO_14yearfirms_full_address.json",
         needs=[I(S5, "geo_SIPO_14yearfirms_full_address.json")]),
    step("14a", 5, "14a_extract_failed_geocodes.py", "input", "geo_Realrenewable_firmsMC_full_address.json",
         needs=[I(S5, "geo_Realrenewable_firmsMC_full_address.json")]),
    *[step("15", 5, "15_geocode_json_to_csv.py", "input", geo_json, needs=[I(S5, geo_json)])
      for _, geo_json in GEO_STEMS],
    # 16 reads the completed geocode files supplied in inputs/ (2 addresses retried, 2 geocoded by hand)
    step("16", 5, "16_find_nearby_firms_distances.py", "input",
         "geo_Realrenewable_firmsMC_full_address_addresses.csv", "geo_SIPO_14yearfirms_full_address_FINAL.csv",
         needs=[I(S5, "geo_Realrenewable_firmsMC_full_address_addresses.csv"),
                I(S5, "geo_SIPO_14yearfirms_full_address_FINAL.csv")]),
    step("16", 5, "16_find_nearby_firms_distances.py", "input",
         "geo_NonRenewable2013NamesFilled_cleaned_full_address_addresses.csv", "geo_SIPO_14yearfirms_full_address_FINAL.csv",
         copy=[(O(S5, "geo_NonRenewable2013NamesFilled_cleaned_full_address_addresses.csv"),
                I(S5, "geo_NonRenewable2013NamesFilled_cleaned_full_address_addresses.csv"))],
         needs=[I(S5, "geo_SIPO_14yearfirms_full_address_FINAL.csv")]),

    # ---- stage 6: industry codes (one modal code per firm)
    step("18", 6, "18_firm_char_converter.py",
         copy=[(O(S1, "firm_characteristics_14year_firms.csv"), I(S6, "firm_characteristics_by_year_firm_code.csv"))]),

    # ---- stage 7: the four Stata-ready firm x plant x year panels
    step("19", 7, "19_join_data_together.py", "main",
         copy=[(O(S6, "firm_14plus_years_2013_codes_converted.csv"), I(S7, "firm_14plus_years_2013_codes_converted.csv")),
               (O(S5, NEARBY_REAL), I(S7, NEARBY_REAL)),
               (O(S5, NEARBY_PLACEBO), I(S7, NEARBY_PLACEBO)),
               (I(S5, f"{PLACEBO_LIST}.csv"), I(S7, f"{PLACEBO_LIST}.csv")),
               (O(S4, f"{AGG}_14years.csv"), I(S7, f"{AGG}_14years.csv")),
               (O(S4, f"{AGG}_14years_CONVERTEDNOMULTIASSIGNEE.csv"), I(S7, f"{AGG}_14years_CONVERTEDNOMULTIASSIGNEE.csv")),
               (O(S4, f"{AGG}_14years_NO_MANUAL_2010_2013.csv"), I(S7, f"{AGG}_14years_NO_MANUAL_2010_2013.csv")),
               (I(S5, RENEWABLE_LIST), I(S7, RENEWABLE_LIST))]),
    step("19", 7, "19_join_data_together.py", "nomulti"),
    step("19", 7, "19_join_data_together.py", "placebo"),
    step("19", 7, "19_join_data_together.py", "nomanual"),

    # ---- stage 8: the three static maps for the paper
    step("21", 8, "21_make_static_firm_map_renewable_nonrenewable.py",
         copy=[(I(S5, RENEWABLE_LIST), I(S8, RENEWABLE_LIST)),
               (I(S5, "geo_Realrenewable_firmsMC_full_address_addresses.csv"),
                I(S8, "geo_Realrenewable_firmsMC_full_address_addresses.csv")),
               (I(S5, "geo_SIPO_14yearfirms_full_address_FINAL.csv"), I(S8, "geo_SIPO_14yearfirms_full_address_FINAL.csv"))],
         needs=[S8 / "map_source" / "ne_10m_admin_1_states_provinces.zip"]),
]

STAGE_DIR = {1: S1, 2: S2, 3: S3, 4: S4, 5: S5, 6: S6, 7: S7, 8: S8}


def rel(p):
    try:
        return Path(p).relative_to(ROOT).as_posix()
    except ValueError:
        return str(p)


def setup_folders():
    """Create every stage's inputs/ and outputs/ folder and the folders the supplied data go in. They are not in
    the repository (data and outputs are not tracked), and most scripts write straight into outputs/."""
    folders = {d for s in STAGE_DIR.values() for d in (s / "inputs", s / "outputs")}
    folders |= {Path(p).parent for st in STEPS for p in st["needs"]}
    for d in sorted(folders):
        d.mkdir(parents=True, exist_ok=True)
    return sorted(folders)


def handoff(src, dst):
    if not src.exists() and dst.exists():
        print(f"using supplied {rel(dst)}", flush=True)   # earlier stage not run; the intermediate file is supplied
        return
    if not src.exists():
        raise FileNotFoundError(f"{rel(src)} is missing: it is written by an earlier step, or is a supplied input "
                                f"(see README.md, 'Data')")
    s = src.stat()
    if dst.exists():
        d = dst.stat()
        if not os.path.samefile(src, dst) and d.st_size == s.st_size and int(d.st_mtime) == int(s.st_mtime):
            return     # already in place as its own copy (copy2 keeps the modification time)
        dst.unlink()   # an outdated (or hard-linked) copy: replace it
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def run_step(st):
    script = STAGE_DIR[st["stage"]] / st["script"]
    print(f"\n=== [{st['stage']}] {st['label']}", flush=True)
    for src, dst in st["copy"]:
        handoff(src, dst)
    missing = [rel(p) for p in st["needs"] if not Path(p).exists()]
    if missing:
        raise FileNotFoundError("missing supplied input(s) - see README.md, 'Data':\n    " + "\n    ".join(missing))
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    rc = subprocess.run([sys.executable, str(script), *map(str, st["args"])], cwd=str(script.parent), env=env).returncode
    if rc != 0:
        raise RuntimeError(f"{st['script']} exited with code {rc}")
    for src, dst in st["after"]:
        handoff(src, dst)


def parse_stages(tokens):
    out = set()
    for t in tokens:
        a, _, b = t.partition("-")
        out.update(range(int(a), int(b or a) + 1))
    bad = out - set(STAGE_DIR)
    if bad:
        sys.exit(f"unknown stage(s): {sorted(bad)} (stages are 1-8)")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stages", nargs="+", metavar="N", help="stages to run, e.g. 5 6 7 or 2-4 (default: all)")
    ap.add_argument("--scripts", nargs="+", metavar="ID", help="scripts to run by number, e.g. 12 19 or 14a")
    ap.add_argument("--filter-patents", action="store_true", help="also run 3_filter_patents.py (raw patent file)")
    ap.add_argument("--geocode", action="store_true", help="also run 14_gaodelocate.py (paid Gaode API)")
    ap.add_argument("--list", action="store_true", help="list the steps and exit")
    ap.add_argument("--setup-folders", action="store_true", help="only create the inputs/, outputs/ and data folders")
    ap.add_argument("--from-intermediate", action="store_true",
                    help="skip the steps that need raw ASIE or patent data (see README.md, 'Running from the intermediate data')")
    a = ap.parse_args()

    if a.list:
        for st in STEPS:
            opt = {"filter": "  [--filter-patents]", "geocode": "  [--geocode]"}.get(st["optional"], "")
            opt += "  [raw data]" if st["id"] in RAW_STEPS else ""
            print(f"  stage {st['stage']}  {st['id']:>4}  {st['label']}{opt}")
        return

    folders = setup_folders()
    if a.setup_folders:
        print("Folders ready (put the supplied data in them, see README.md, 'Data'):")
        for d in folders:
            print(f"  {rel(d)}/")
        return

    flags = {"filter": a.filter_patents, "geocode": a.geocode}
    if a.scripts:
        ids = set(a.scripts)
        unknown = ids - {st["id"] for st in STEPS}
        if unknown:
            sys.exit(f"unknown script id(s): {sorted(unknown)} (see --list)")
        chosen = [st for st in STEPS if st["id"] in ids]
    else:
        stages = parse_stages(a.stages) if a.stages else set(STAGE_DIR)
        chosen = [st for st in STEPS if st["stage"] in stages and (not st["optional"] or flags[st["optional"]])]
        if a.from_intermediate:
            chosen = [st for st in chosen if st["id"] not in RAW_STEPS]

    for n_done, st in enumerate(chosen):
        try:
            run_step(st)
        except (FileNotFoundError, RuntimeError) as e:
            print(f"\nFAILED at {st['label']}: {e}")
            print(f"{n_done} of {len(chosen)} steps completed.")
            sys.exit(1)
    print(f"\nAll {len(chosen)} steps completed.")


if __name__ == "__main__":
    main()
