"""
DRIMS flood data extractor
---------------------------
Reads monthly DRIMS API JSON exports, flattens them into a tidy per-
(district, revenue_circle, timeperiod) table, matches revenue circles to
the Assam revenue-circle geojson via fuzzy matching, and writes one CSV
per indicator per timeperiod for downstream use.

Just edit the three paths below to match your machine, then run:
    python drims_extractor.py
"""

from __future__ import annotations

import logging
import os
import re
from functools import reduce
from typing import Any, Callable, Dict, List, Optional, Union

import pandas as pd
import geopandas as gpd
from fuzzywuzzy import process

# -----------------------------------------------------------------------------
# Config — edit these three paths for your machine
# -----------------------------------------------------------------------------

DATA_DIR = os.path.join(os.getcwd(), "Sources", "DRIMS", "data", "DRIMS_api_output")
GEOJSON_PATH = os.path.join(os.getcwd(), "Maps", "Geojson", "assam_rc_2024-11.geojson")
OUTPUT_DIR = os.path.join(os.getcwd(), "Sources", "DRIMS", "data", "variables")

INDICATOR_RENAME = {
    "Population Affected": "Population_affected_Total",
    "Crop Area": "Crop_Area",
    "bridgeAffected": "Bridge",
    "lives_lost_confirmed": "Human_Live_Lost",
    "lives_lost_missing": "Human_Live_Missing",
    "embBreached": "Embankment breached",
    "embAffected": "Embankments affected",
    "roadAffected": "Roads",
    "reliefCamps": "Relief Camps",
    "reliefCenters": "Relief Centers",
    "relief_inmates": "Relief Inmates",
}

INDICATOR_COLUMNS = [
    "Population_affected_Total",
    "Crop_Area",
    "Bridge",
    "Embankment breached",
    "Embankments affected",
    "Roads",
    "Human_Live_Lost",
    "Relief Camps",
    "Relief Centers",
    "Relief Inmates",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("drims_extractor")


# -----------------------------------------------------------------------------
# Generic parsing utilities
# -----------------------------------------------------------------------------

def parse_paren_text(text: str) -> List[str]:
    """Extract substrings inside parentheses, e.g. '(A | 1), (B | 2)' -> ['A | 1', 'B | 2']"""
    return re.findall(r"\(\s*(.*?)\s*\)", text or "")


def extract_from_list(
    data_list: List[Dict[str, Any]],
    detail_key: str,
    value_name: str,
    cast_fn: Callable[[str], Any] = lambda x: x,
) -> pd.DataFrame:
    """
    Extracts (revenue_circle | value) entries from each dict in data_list under detail_key.
    Returns a DataFrame with columns ['district', 'revenue_circle', value_name], even if empty.
    """
    records = []
    for entry in data_list:
        district = entry.get("district")
        text = entry.get(detail_key, "")
        for item in parse_paren_text(text):
            parts = [p.strip() for p in item.split("|", 1)]
            if len(parts) != 2:
                continue
            rev_circle, raw_val = parts
            try:
                val = cast_fn(raw_val)
            except Exception:
                continue
            records.append({"district": district, "revenue_circle": rev_circle, value_name: val})

    df = pd.DataFrame(records)
    for col in ["district", "revenue_circle", value_name]:
        if col not in df.columns:
            df[col] = pd.Series(dtype="object")
    return df


def extract_from_dict_of_lists(data_dict: Dict[str, List[Dict[str, Any]]]) -> pd.DataFrame:
    """Flatten a dict of lists (e.g. infrastructure indicators) into a wide table."""
    rows = []
    for indicator, entries in data_dict.items():
        for entry in entries:
            district = entry.get("district")
            for detail in entry.get("details", []):
                block_text = detail.get("block", "")
                for item in parse_paren_text(block_text):
                    parts = [p.strip() for p in item.split("|", 1)]
                    if len(parts) != 2:
                        continue
                    rev_circle, raw_val = parts
                    try:
                        val = int(raw_val)
                    except ValueError:
                        continue
                    rows.append({"district": district, "revenue_circle": rev_circle, indicator: val})

    df = pd.DataFrame(rows)
    if df.empty:
        cols = ["district", "revenue_circle"] + list(data_dict.keys())
        return pd.DataFrame(columns=cols)

    return df.groupby(["district", "revenue_circle"], as_index=False).agg(
        {ind: "sum" for ind in data_dict.keys()}
    )


def extract_human_lives(human_dict: Dict[str, Any], detail_key: str = "details") -> pd.DataFrame:
    """Extract lives_lost_confirmed and lives_lost_missing."""
    df_confirmed = extract_from_list(human_dict.get("confirmed", []), detail_key, "lives_lost_confirmed", cast_fn=int)
    df_missing = extract_from_list(human_dict.get("missing", []), detail_key, "lives_lost_missing", cast_fn=int)
    df = pd.merge(df_confirmed, df_missing, on=["district", "revenue_circle"], how="outer")
    for col in ["lives_lost_confirmed", "lives_lost_missing"]:
        if col not in df.columns:
            df[col] = 0
    return df


def extract_relief_inmates(
    data_list: List[Dict[str, Any]],
    detail_key: str = "details",
    value_name: str = "relief_inmates",
) -> pd.DataFrame:
    """Extracts (revenue_circle | inmate_count) entries from campInmates."""
    return extract_from_list(
        data_list,
        detail_key,
        value_name,
        cast_fn=lambda x: int(re.search(r"\d+", x).group()),
    )


def extract_relief_camps_centers(relief_list: List[Dict[str, Any]]) -> pd.DataFrame:
    """Extracts reliefCamps and reliefCenters counts per district/revenue_circle."""
    records = []
    for entry in relief_list:
        district = entry.get("district")
        for key in ["reliefCamps", "reliefCenters"]:
            text = entry.get(key, "")
            for item in parse_paren_text(text):
                parts = [p.strip() for p in item.split("|", 1)]
                if len(parts) != 2:
                    continue
                rev_circle, raw_val = parts
                try:
                    val = int(re.search(r"\d+", raw_val).group())
                except Exception:
                    val = 0
                records.append({"district": district, "revenue_circle": rev_circle, key: val})

    df = pd.DataFrame(records)
    if df.empty:
        return pd.DataFrame(columns=["district", "revenue_circle", "reliefCamps", "reliefCenters"])
    return df.groupby(["district", "revenue_circle"], as_index=False).agg(
        {"reliefCamps": "sum", "reliefCenters": "sum"}
    )


# -----------------------------------------------------------------------------
# Main JSON extraction
# -----------------------------------------------------------------------------

def extract_json(data_source: Union[str, Any], timeperiod: str) -> Optional[pd.DataFrame]:
    """Load one DRIMS JSON file and flatten it into a single tidy DataFrame."""
    import json

    try:
        if isinstance(data_source, str):
            if os.path.getsize(data_source) == 0:
                logger.warning("Skipping empty file: %s", data_source)
                return None
            with open(data_source, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = json.load(data_source)
    except Exception as e:
        logger.warning("Skipping unreadable JSON (%s): %s", data_source, e)
        return None

    # Population & crop area
    ap = data.get("affectedPopulation", [])
    pop_records, crop_records = [], []
    for entry in ap:
        district = entry.get("district")
        details = entry.get("details", "")
        for chunk in parse_paren_text(details):
            parts = [p.strip() for p in chunk.split("|")]
            if len(parts) != 3:
                continue
            rev_circle, pop_raw, crop_raw = parts

            pop_match = re.search(r"\d+", pop_raw)
            if pop_match:
                pop_records.append(
                    {"district": district, "revenue_circle": rev_circle, "Population Affected": int(pop_match.group())}
                )
            crop_match = re.search(r"\d+(?:\.\d+)?", crop_raw)
            if crop_match:
                crop_records.append(
                    {"district": district, "revenue_circle": rev_circle, "Crop Area": float(crop_match.group())}
                )

    df_pop = pd.DataFrame(pop_records, columns=["district", "revenue_circle", "Population Affected"])
    df_crop = pd.DataFrame(crop_records, columns=["district", "revenue_circle", "Crop Area"])
    df_pop_crop = pd.merge(df_pop, df_crop, on=["district", "revenue_circle"], how="outer").fillna(0)

    df_hll = extract_human_lives(data.get("hllDetails", {}))
    df_inf = extract_from_dict_of_lists(data.get("infDamageDetails", {}))
    df_rel = extract_relief_camps_centers(data.get("reliefCampsAndCenters", []))
    df_inmates = extract_relief_inmates(data.get("campInmates", []))

    dfs = [df_pop_crop, df_hll, df_inf, df_rel, df_inmates]
    final_df = reduce(
        lambda left, right: pd.merge(left, right, on=["district", "revenue_circle"], how="outer"),
        dfs,
    ).fillna(0)

    final_df["timeperiod"] = timeperiod
    return final_df


def extract_folder(folder_path: str, pattern: str = r"^.+\.json$") -> pd.DataFrame:
    """Process every JSON file in a folder into one combined DataFrame."""
    frames = []
    n_seen, n_skipped = 0, 0

    for fname in sorted(os.listdir(folder_path)):
        if not re.match(pattern, fname):
            continue
        n_seen += 1
        timeperiod = os.path.splitext(fname)[0]
        path = os.path.join(folder_path, fname)
        df = extract_json(path, timeperiod)
        if df is not None and not df.empty:
            frames.append(df)
        else:
            n_skipped += 1

    logger.info("Processed %d JSON files, skipped %d empty/invalid.", n_seen, n_skipped)
    if not frames:
        logger.error("No usable JSON files found in %s", folder_path)
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


# -----------------------------------------------------------------------------
# Geo matching + export
# -----------------------------------------------------------------------------

def fuzzy_merge(df_1: pd.DataFrame, df_2: pd.DataFrame, key1: str, key2: str, threshold: int = 90, limit: int = 2) -> pd.DataFrame:
    """
    Fuzzy-match df_1[key1] values against df_2[key2] values.
    Adds a 'matches' column to df_1 with comma-joined matches above `threshold`.
    """
    choices = df_2[key2].tolist()
    matches = df_1[key1].apply(lambda x: process.extract(x, choices, limit=limit))
    df_1 = df_1.copy()
    df_1["matches"] = matches.apply(lambda x: ", ".join(i[0] for i in x if i[1] >= threshold))
    return df_1


def build_master_table(data_dir: str, geojson_path: str) -> pd.DataFrame:
    """Run the full pipeline: extract, rename, fuzzy-match revenue circles, filter, clean."""
    master_df = extract_folder(data_dir)
    if master_df.empty:
        return master_df

    master_df = master_df.rename(columns=INDICATOR_RENAME)
    master_df["district_2"] = master_df["district"].str.upper()

    rc_gdf = gpd.read_file(geojson_path)
    fuzzymatch = fuzzy_merge(rc_gdf, master_df, "revenue_ci", "revenue_circle", threshold=80, limit=1)

    filtered_df = master_df[(master_df[INDICATOR_COLUMNS] != 0).any(axis=1)]

    rc_complete_matched = fuzzymatch.merge(
        filtered_df,
        left_on=["matches", "dtname"],
        right_on=["revenue_circle", "district_2"],
        how="outer",
    )
    rc_complete_matched = rc_complete_matched[
        ["revenue_ci", "object_id", "dtname", "district_2", "timeperiod"] + INDICATOR_COLUMNS
    ]

    df_cleaned = rc_complete_matched.dropna(subset=["timeperiod", "object_id"])
    df_cleaned = df_cleaned[
        ["district_2", "revenue_ci", "object_id", "dtname", "timeperiod"] + INDICATOR_COLUMNS
    ]
    df_cleaned = df_cleaned.rename(columns={"district_2": "DISTRICT"})
    return df_cleaned


def export_indicator_csvs(df_cleaned: pd.DataFrame, output_dir: str) -> None:
    """Write one CSV per indicator per timeperiod, matching the original variable-export layout."""
    for indicator in INDICATOR_COLUMNS:
        indicator_dir = os.path.join(output_dir, indicator)
        os.makedirs(indicator_dir, exist_ok=True)
        for timeperiod in df_cleaned["timeperiod"].unique():
            subset = df_cleaned[["object_id", indicator]][df_cleaned["timeperiod"] == timeperiod]
            filename = f"{indicator}_{timeperiod}.csv"
            subset.to_csv(os.path.join(indicator_dir, filename), index=False)
    logger.info("Exported indicator CSVs to %s", output_dir)


# -----------------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------------

def main():
    logger.info("Data dir: %s", DATA_DIR)
    logger.info("Geojson: %s", GEOJSON_PATH)
    logger.info("Output dir: %s", OUTPUT_DIR)

    df_cleaned = build_master_table(DATA_DIR, GEOJSON_PATH)
    if df_cleaned.empty:
        logger.error("Pipeline produced no data — check DATA_DIR and GEOJSON_PATH at the top of this script.")
        return

    export_indicator_csvs(df_cleaned, OUTPUT_DIR)


if __name__ == "__main__":
    main()