"""Stage 8: the paper's three static maps of China.

  map_manufacturing_firms.png                 the manufacturing firms (the patenting 14-year sample firms)
  map_renewable_firms.png                     the renewable-energy equipment makers, by type
  map_manufacturing_and_renewable_firms.png   both layers

Boundaries: Natural Earth 1:10m admin-1 states and provinces (public domain; "Made with Natural Earth"),
read unmodified from map_source/. Also writes merged_renewable_with_firm_codes.csv (plants + 行业小类代码).
"""
import argparse
import os
from pathlib import Path

import geopandas as gpd
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

# Read from inputs/ and map_source/, write to outputs/ next to this script
_HERE = os.path.dirname(os.path.abspath(__file__))
I = lambda *p: os.path.join(_HERE, 'inputs', *p)
O = lambda *p: os.path.join(_HERE, 'outputs', *p)
MAP_SOURCE = os.path.join(_HERE, 'map_source', 'ne_10m_admin_1_states_provinces.zip')

# Albers equal-area conic centred on China
CHINA_ALBERS = "+proj=aea +lat_1=25 +lat_2=47 +lat_0=0 +lon_0=105 +datum=WGS84 +units=m +no_defs"

CODE_COLOR_MAP = {
    "3825": "red",    # photovoltaic cells
    "3415": "green",  # wind turbines
    "3414": "blue",   # water turbines
}
RENEWABLE_LEGEND = [("3825", "Photovoltaic cell firms"), ("3415", "Wind turbine firms"), ("3414", "Water turbine firms")]
MANUFACTURING_COLOR = "#8795AA"
MANUFACTURING_LABEL = "Manufacturing firms"
LAND_COLOR = "#e6e6e6"

# label nudges (lon, lat degrees) for provinces too small or crowded to label at their centre
LABEL_OFFSETS = {"Beijing": (-1.2, 0.9), "Tianjin": (2.2, 0.2), "Shanghai": (2.6, 0.0), "Hainan": (0.0, -1.3)}


def read_csv_with_fallback(path: str) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path)


def gcj02_to_wgs84(lon: np.ndarray, lat: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Gaode returns GCJ-02 coordinates, offset ~0.1-0.7 km from the WGS84 of the Natural Earth boundaries.
    Standard inverse of the published GCJ-02 obfuscation (accurate to a few metres)."""
    a, ee = 6378245.0, 0.00669342162296594323
    x, y = lon - 105.0, lat - 35.0
    dlat = (-100 + 2 * x + 3 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * np.sqrt(np.abs(x))
            + (20 * np.sin(6 * x * np.pi) + 20 * np.sin(2 * x * np.pi)) * 2 / 3
            + (20 * np.sin(y * np.pi) + 40 * np.sin(y / 3 * np.pi)) * 2 / 3
            + (160 * np.sin(y / 12 * np.pi) + 320 * np.sin(y * np.pi / 30)) * 2 / 3)
    dlon = (300 + x + 2 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * np.sqrt(np.abs(x))
            + (20 * np.sin(6 * x * np.pi) + 20 * np.sin(2 * x * np.pi)) * 2 / 3
            + (20 * np.sin(x * np.pi) + 40 * np.sin(x / 3 * np.pi)) * 2 / 3
            + (150 * np.sin(x / 12 * np.pi) + 300 * np.sin(x / 30 * np.pi)) * 2 / 3)
    rad = lat / 180 * np.pi
    magic = 1 - ee * np.sin(rad) ** 2
    dlat = dlat * 180 / ((a * (1 - ee)) / (magic * np.sqrt(magic)) * np.pi)
    dlon = dlon * 180 / (a / np.sqrt(magic) * np.cos(rad) * np.pi)
    return lon - dlon, lat - dlat


def prepare_geodata(df: pd.DataFrame) -> gpd.GeoDataFrame:
    out = df.copy()
    out["经度"] = pd.to_numeric(out["经度"], errors="coerce")
    out["纬度"] = pd.to_numeric(out["纬度"], errors="coerce")
    out = out.dropna(subset=["经度", "纬度"])
    lon, lat = gcj02_to_wgs84(out["经度"].to_numpy(float), out["纬度"].to_numpy(float))
    return gpd.GeoDataFrame(out, geometry=gpd.points_from_xy(lon, lat), crs="EPSG:4326").to_crs(CHINA_ALBERS)


def build_color_column(df: gpd.GeoDataFrame) -> pd.Series:
    # A code read as '3825.0' is normalised, and a code outside the three mapped ones is drawn in grey
    # (otherwise matplotlib raises "Invalid RGBA argument"). All 640 current plants are 3825/3414/3415.
    codes = df["firm_code"].astype(str).str.replace(r"\.0$", "", regex=True)
    return codes.map(CODE_COLOR_MAP).fillna("grey")


def merge_renewable_with_industry_codes(
    renewable_geo_df: pd.DataFrame,
    renewable_list_df: pd.DataFrame,
) -> pd.DataFrame:
    renewable = renewable_geo_df.copy()
    codes = renewable_list_df.copy()

    renewable["org_id_norm"] = renewable["组织机构代码"].astype(str).str.strip().str.replace(".0", "", regex=False)
    renewable["name_norm"] = renewable["企业名称"].astype(str).str.strip()

    codes["org_id_norm"] = codes["组织机构代码"].astype(str).str.strip().str.replace(".0", "", regex=False)
    codes["name_norm"] = codes["企业名称"].astype(str).str.strip()
    codes["firm_code_from_all_underused"] = codes["行业小类代码"].astype(str).str.strip()

    # First merge by organization code to preserve exact firm identity when available.
    code_by_id = codes[["org_id_norm", "firm_code_from_all_underused"]].dropna().drop_duplicates(
        subset=["org_id_norm"], keep="first"
    )
    renewable = renewable.merge(code_by_id, on="org_id_norm", how="left")

    # Fill unmatched rows by firm name as fallback.
    code_by_name = codes[["name_norm", "firm_code_from_all_underused"]].dropna().drop_duplicates(
        subset=["name_norm"], keep="first"
    )
    name_lookup = code_by_name.set_index("name_norm")["firm_code_from_all_underused"].to_dict()
    missing_mask = renewable["firm_code_from_all_underused"].isna()
    renewable.loc[missing_mask, "firm_code_from_all_underused"] = renewable.loc[missing_mask, "name_norm"].map(name_lookup)

    renewable["firm_code"] = renewable["firm_code_from_all_underused"].astype("string")
    return renewable.drop(columns=["org_id_norm", "name_norm"], errors="ignore")


def load_boundaries(path: str):
    """China's provinces (one feature each, English names) and unlabelled Hong Kong / Macau outlines."""
    ne = gpd.read_file(f"zip://{path}")
    prov = ne[(ne["adm0_a3"] == "CHN") & (ne["name_en"] != "Paracel Islands")]
    prov = prov.dissolve(by="name_en", as_index=False)[["name_en", "geometry"]]
    other = ne[ne["adm0_a3"].isin(["HKG", "MAC"])].dissolve(by="adm0_a3", as_index=False)
    return prov, other


def draw_base(ax, prov: gpd.GeoDataFrame, other: gpd.GeoDataFrame, show_labels: bool) -> None:
    prov_p = prov.to_crs(CHINA_ALBERS)
    other.to_crs(CHINA_ALBERS).plot(ax=ax, color=LAND_COLOR, edgecolor="white", linewidth=0.4, zorder=0)
    prov_p.plot(ax=ax, color=LAND_COLOR, edgecolor="white", linewidth=0.6, zorder=0)

    # extent: mainland + Hainan (the far South China Sea islands are left out of the frame)
    xmin, ymin, xmax, ymax = prov_p.total_bounds
    pad = 0.02 * (xmax - xmin)
    ax.set_xlim(xmin - pad, xmax + pad)
    ax.set_ylim(ymin - pad, ymax + pad)
    ax.set_aspect("equal")
    ax.set_axis_off()

    if show_labels:
        pts = prov.geometry.representative_point()
        for name, pt in zip(prov["name_en"], pts):
            dx, dy = LABEL_OFFSETS.get(name, (0.0, 0.0))
            xy = gpd.GeoSeries(gpd.points_from_xy([pt.x + dx], [pt.y + dy]), crs="EPSG:4326").to_crs(CHINA_ALBERS)
            ax.text(xy.x.iloc[0], xy.y.iloc[0], name, fontsize=6.5, ha="center", va="center", color="#333333",
                    zorder=5, path_effects=[pe.withStroke(linewidth=2, foreground="white")])


def plot_manufacturing(ax, gdf: gpd.GeoDataFrame, size: float) -> None:
    gdf.plot(ax=ax, marker="o", markersize=size, color=MANUFACTURING_COLOR, edgecolor=MANUFACTURING_COLOR,
             linewidth=0.2, alpha=0.85, zorder=2)


def plot_renewable(ax, gdf: gpd.GeoDataFrame, size: float) -> None:
    gdf.plot(ax=ax, marker="o", markersize=size, color=build_color_column(gdf), edgecolor="white",
             linewidth=0.3, alpha=0.9, zorder=3)


def legend(ax, manufacturing: bool, renewable: bool) -> None:
    dot = lambda color, label, edge="white": Line2D([0], [0], marker="o", linestyle="", markersize=6,
                                                    markerfacecolor=color, markeredgecolor=edge, label=label)
    handles = []
    if manufacturing:
        handles.append(dot(MANUFACTURING_COLOR, MANUFACTURING_LABEL, MANUFACTURING_COLOR))
    if renewable:
        handles += [dot(CODE_COLOR_MAP[c], label) for c, label in RENEWABLE_LEGEND]
    ax.legend(handles=handles, loc="lower left", frameon=True, framealpha=1, edgecolor="black",
              fancybox=False, fontsize=9)


def save(fig, path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved map: {Path(path).name}")


def main(args: argparse.Namespace) -> None:
    renewable_df = read_csv_with_fallback(args.renewable_csv)
    manufacturing_df = read_csv_with_fallback(args.manufacturing_csv)
    renewable_list_df = read_csv_with_fallback(args.renewable_codes_csv)

    renewable_df = merge_renewable_with_industry_codes(renewable_df, renewable_list_df)
    # Keep manufacturing firms only when they are not duplicated by firm name in renewable (never drawn twice).
    renewable_names = set(renewable_df["企业名称"].dropna().astype(str).str.strip())
    manufacturing_df = manufacturing_df[~manufacturing_df["企业名称"].astype(str).str.strip().isin(renewable_names)]

    # Renewable firms should carry firm_code (行业小类代码 from the renewable list) for color mapping.
    renewable_df = renewable_df[renewable_df["firm_code"].notna()]
    renewable_df.to_csv(args.merged_renewable_output_csv, index=False, encoding="utf-8-sig")
    print(f"Saved merged renewable data to: {Path(args.merged_renewable_output_csv).name}")

    gdf_renewable = prepare_geodata(renewable_df)
    gdf_manufacturing = prepare_geodata(manufacturing_df)
    prov, other = load_boundaries(args.boundary)
    labels = not args.hide_province_labels

    for out, show_m, show_r in ((args.manufacturing_output, True, False),
                                (args.renewable_output, False, True),
                                (args.combined_output, True, True)):
        fig, ax = plt.subplots(figsize=(10, 8))
        draw_base(ax, prov, other, labels)
        if show_m:
            plot_manufacturing(ax, gdf_manufacturing, args.marker_size * (0.5 if show_r else 0.8))
        if show_r:
            plot_renewable(ax, gdf_renewable, args.marker_size)
        legend(ax, show_m, show_r)
        save(fig, out)

    print(f"Renewable firms plotted: {len(gdf_renewable)} "
          f"({gdf_renewable['firm_code'].astype(str).value_counts().to_dict()})")
    print(f"Manufacturing firms plotted: {len(gdf_manufacturing)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create the three static China firm maps for the paper.")
    parser.add_argument("--renewable-csv", default=I("geo_Realrenewable_firmsMC_full_address_addresses.csv"),
                        help="Geocoded renewable-energy firms CSV.")
    parser.add_argument("--manufacturing-csv", default=I("geo_SIPO_14yearfirms_full_address_FINAL.csv"),
                        help="Geocoded manufacturing (sample) firms CSV.")
    parser.add_argument("--boundary", default=MAP_SOURCE,
                        help="Natural Earth ne_10m_admin_1_states_provinces.zip.")
    parser.add_argument("--renewable-codes-csv", default=I("ASIE_Renewables_Firms_2000-2013.csv"),
                        help="Renewable-maker list for the firm-code lookup (column: 行业小类代码).")
    parser.add_argument("--merged-renewable-output-csv", default=O("merged_renewable_with_firm_codes.csv"),
                        help="Output CSV: renewable geodata merged with 行业小类代码.")
    parser.add_argument("--manufacturing-output", default=O("map_manufacturing_firms.png"))
    parser.add_argument("--renewable-output", default=O("map_renewable_firms.png"))
    parser.add_argument("--combined-output", default=O("map_manufacturing_and_renewable_firms.png"))
    parser.add_argument("--hide-province-labels", action="store_true", help="Hide province labels.")
    parser.add_argument("--marker-size", type=float, default=8, help="Marker size for renewable firms.")
    return parser.parse_args()


if __name__ == "__main__":
    main(parse_args())
