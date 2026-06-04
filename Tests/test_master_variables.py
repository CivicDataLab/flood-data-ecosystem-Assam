"""
Integration tests for Sources/MASTER_VARIABLES.csv.

These tests verify the correctness of the final assembled model-input table.
Each test is named after the data-quality issue it guards against; many were
first identified in the June 2026 audit of the file.
"""
import pandas as pd
import pytest

from helpers import ROOT, SOURCES, skip_if_missing

MASTER_PATH = SOURCES / "MASTER_VARIABLES.csv"

EXPECTED_ROWS = 11160       # 180 RCs × 62 months (2021-04 → 2026-05)
EXPECTED_COLS = 85
EXPECTED_RCS  = 180
EXPECTED_TPS  = 62
FIRST_TP      = "2021_04"
LAST_TP       = "2026_05"

# Columns that must be present in the output
REQUIRED_COLUMNS = [
    "object_id", "district", "rc_area", "timeperiod",
    "total_tender_awarded_value", "erosion_tenders_awarded_value",
    "SOPD_tenders_awarded_value", "SDRF_sanctions_awarded_value",
    "SDRF_tenders_awarded_value", "RIDF_tenders_awarded_value",
    "LTIF_tenders_awarded_value", "CIDF_tenders_awarded_value",
    "Preparedness Measures_tenders_awarded_value",
    "Immediate Measures_tenders_awarded_value",
    "Others_tenders_awarded_value",
    "Repair and Restoration_tenders_awarded_value",
    "Total_Animal_Washed_Away", "Total_Animal_Affected",
    "Population_affected_Total", "Crop_Area",
    "Male_Camp", "Female_Camp", "Children_Camp",
    "Total_House_Fully_Damaged",
    "Human_Live_Lost", "Human_Live_Lost_Children",
    "Human_Live_Lost_Female", "Human_Live_Lost_Male",
    "Embankments affected", "Roads", "Bridge", "Embankment breached",
    "max_rain", "mean_rain", "sum_rain",
    "mean_ndvi", "mean_ndbi", "count",
    "inundation_pct", "inundation_intensity_mean",
    "inundation_intensity_mean_nonzero", "inundation_intensity_sum",
    "riverlevel_mean", "riverlevel_min", "riverlevel_max",
    "total_expenditure_value", "SDRF_expenditure_value",
    "Immediate Measures_expenditure_value",
    "Others_expenditure_value",
    "Repair and Restoration_expenditure_value",
    "Relief Camps", "Relief Centers", "Relief Inmates", "Relief_Camp_inmates",
    "mean_sex_ratio", "sum_aged_population", "sum_young_population",
    "sum_population",
    "water", "trees", "flooded_vegetation", "crops",
    "built_area", "bare_ground", "clouds", "rangeland",
    "schools_count", "health_centres_count",
    "rail_length", "rail_count", "road_length",
    "mean_cn", "elevation_mean", "slope_mean",
    "revenue_ci", "dtname", "dtcode11",
    "net_sown_area_in_hac", "avg_electricity", "avg_tele",
    "rc_piped_hhds_pct", "rc_nosanitation_hhds_pct", "total_hhd",
    "distance_from_river", "drainage_density",
]

# Columns that must always be >= 0
NON_NEGATIVE_COLS = [
    "total_tender_awarded_value", "erosion_tenders_awarded_value",
    "SDRF_sanctions_awarded_value", "SDRF_tenders_awarded_value",
    "RIDF_tenders_awarded_value", "LTIF_tenders_awarded_value",
    "CIDF_tenders_awarded_value", "total_expenditure_value",
    "SDRF_expenditure_value",
    "Total_Animal_Washed_Away", "Total_Animal_Affected",
    "Population_affected_Total", "Crop_Area",
    "Human_Live_Lost", "Total_House_Fully_Damaged",
    "max_rain", "mean_rain", "sum_rain",
    "inundation_pct",
    "sum_population", "sum_aged_population", "sum_young_population",
    "schools_count", "health_centres_count", "road_length",
    "rc_area", "drainage_density",
]

# Columns that should be constant (same value every month) per revenue circle
STATIC_COLS = [
    "elevation_mean", "slope_mean", "distance_from_river",
    "drainage_density", "schools_count", "health_centres_count",
    "road_length", "mean_cn",
    "net_sown_area_in_hac", "avg_electricity", "avg_tele",
    "rc_piped_hhds_pct", "rc_nosanitation_hhds_pct", "total_hhd",
    "dtname", "dtcode11", "district",
]


# ── Grid integrity ─────────────────────────────────────────────────────────

def test_shape(master_df):
    assert master_df.shape == (EXPECTED_ROWS, EXPECTED_COLS), (
        f"Expected {EXPECTED_ROWS}×{EXPECTED_COLS}, got {master_df.shape}. "
        "This usually means the date range or a variable source has changed."
    )


def test_no_duplicate_keys(master_df):
    dupes = master_df.duplicated(subset=["object_id", "timeperiod"])
    assert not dupes.any(), (
        f"{dupes.sum()} duplicate (object_id, timeperiod) pairs found. "
        "Check for double-merges in master2.py."
    )


def test_full_grid_coverage(master_df, expected_timeperiods):
    actual_tps  = sorted(master_df["timeperiod"].unique())
    actual_rcs  = master_df["object_id"].nunique()
    assert len(actual_tps) == EXPECTED_TPS,   f"Expected {EXPECTED_TPS} timeperiods, got {len(actual_tps)}"
    assert actual_rcs       == EXPECTED_RCS,   f"Expected {EXPECTED_RCS} RCs, got {actual_rcs}"
    assert actual_tps[0]    == FIRST_TP,       f"First timeperiod should be {FIRST_TP}"
    assert actual_tps[-1]   == LAST_TP,        f"Last timeperiod should be {LAST_TP}"
    missing = set(expected_timeperiods) - set(actual_tps)
    assert not missing, f"Missing timeperiods: {sorted(missing)}"


def test_no_null_values(master_df):
    """master2.py fillna(0) should leave no NaNs."""
    null_counts = master_df.isnull().sum()
    nulls = null_counts[null_counts > 0]
    assert nulls.empty, f"Unexpected NaN values:\n{nulls.to_string()}"


def test_required_columns_present(master_df):
    missing = [c for c in REQUIRED_COLUMNS if c not in master_df.columns]
    assert not missing, f"Missing columns: {missing}"


def test_timeperiod_format(master_df):
    import re
    bad = master_df["timeperiod"][
        ~master_df["timeperiod"].str.match(r"^\d{4}_\d{2}$")
    ]
    assert bad.empty, f"Malformed timeperiod values: {bad.unique()}"


# ── Column types ───────────────────────────────────────────────────────────

def test_numeric_tender_columns(master_df):
    tender_cols = [c for c in master_df.columns if "_tenders_awarded_value" in c
                   or "_expenditure_value" in c or "_sanctions_awarded_value" in c]
    for col in tender_cols:
        assert pd.api.types.is_numeric_dtype(master_df[col]), f"{col} is not numeric"


def test_numeric_environmental_columns(master_df):
    for col in ["max_rain", "mean_rain", "sum_rain", "mean_ndvi",
                "mean_ndbi", "inundation_pct", "elevation_mean", "slope_mean"]:
        assert pd.api.types.is_numeric_dtype(master_df[col]), f"{col} is not numeric"


# ── Value sanity ───────────────────────────────────────────────────────────

def test_non_negative_values(master_df):
    for col in NON_NEGATIVE_COLS:
        if col not in master_df.columns:
            continue
        negatives = (master_df[col] < 0).sum()
        assert negatives == 0, f"{negatives} negative values found in '{col}'"


def test_inundation_pct_max_100(master_df):
    over = (master_df["inundation_pct"] > 100).sum()
    assert over == 0, f"{over} rows have inundation_pct > 100%"


def test_mean_rain_le_max_rain(master_df):
    # Allow for floating-point rounding from raster aggregation (tolerance 1e-3 mm)
    violations = (master_df["mean_rain"] > master_df["max_rain"] + 1e-3).sum()
    assert violations == 0, f"{violations} rows where mean_rain materially > max_rain"


def test_riverlevel_mean_between_min_max(master_df):
    """When river level is non-zero, mean must lie in [min, max]."""
    non_zero = master_df[master_df["riverlevel_mean"] > 0]
    above_max = (non_zero["riverlevel_mean"] > non_zero["riverlevel_max"]).sum()
    below_min = (non_zero["riverlevel_mean"] < non_zero["riverlevel_min"]).sum()
    assert above_max == 0, f"{above_max} rows where riverlevel_mean > riverlevel_max"
    assert below_min == 0, f"{below_min} rows where riverlevel_mean < riverlevel_min"


# ── Static / census columns ────────────────────────────────────────────────

def test_static_columns_constant_per_rc(master_df):
    """Columns derived from census/GIS data must not vary across timeperiods."""
    for col in STATIC_COLS:
        if col not in master_df.columns:
            continue
        varying = master_df.groupby("object_id")[col].nunique()
        bad_rcs = varying[varying > 1]
        assert bad_rcs.empty, (
            f"'{col}' varies across timeperiods for {len(bad_rcs)} RCs: "
            f"{bad_rcs.index.tolist()[:5]}"
        )


# ── Known data-source cutoffs (documented gaps) ────────────────────────────

def test_worldpop_coverage_all_years(master_df):
    """sum_population must be positive for every row — WorldPop 2026 projections
    are now populated via linear extrapolation."""
    zeros = (master_df["sum_population"] == 0).sum()
    assert zeros == 0, (
        f"sum_population is 0 for {zeros} rows. "
        "If WorldPop data is missing for a year, run WORLDPOP/scripts/projections.py"
    )


def test_land_cover_missing_from_2024(master_df):
    """Dynamic World land-cover scraper stalled at Dec 2023; all 7 classes must be
    zero from 2024_01 onwards."""
    lc_cols = ["water", "trees", "flooded_vegetation", "crops",
               "built_area", "bare_ground", "rangeland"]
    cutoff_tps = [tp for tp in master_df["timeperiod"].unique()
                  if tp >= "2024_01"]
    sub = master_df[master_df["timeperiod"].isin(cutoff_tps)]
    for col in lc_cols:
        non_zero = (sub[col] != 0).sum()
        assert non_zero == 0, (
            f"'{col}' has {non_zero} non-zero rows from 2024_01 onwards. "
            "Land-cover scraper may have been re-run — update this test if intentional."
        )


def test_land_cover_present_before_2024(master_df):
    """At least one land-cover class should be non-zero in any pre-2024 month."""
    lc_cols = ["water", "trees", "flooded_vegetation", "crops",
               "built_area", "bare_ground", "rangeland"]
    pre_2024 = master_df[master_df["timeperiod"] < "2024_01"]
    for col in lc_cols:
        non_zero = (pre_2024[col] > 0).sum()
        assert non_zero > 0, f"'{col}' is all-zero before 2024 — unexpected"


def test_riverlevel_missing_from_2024_06(master_df):
    """River-level ingestion stopped after May 2024."""
    stale_tps = [tp for tp in master_df["timeperiod"].unique()
                 if tp >= "2024_06"]
    sub = master_df[master_df["timeperiod"].isin(stale_tps)]
    non_zero = (sub["riverlevel_mean"] != 0).sum()
    assert non_zero == 0, (
        f"riverlevel_mean has {non_zero} non-zero rows from 2024_06 onwards. "
        "River-level data may have been updated — update this test if intentional."
    )


def test_riverlevel_present_before_2024_06(master_df):
    """River level must have been collected through May 2024."""
    present_tps = master_df[master_df["timeperiod"] <= "2024_05"]
    non_zero = (present_tps["riverlevel_mean"] > 0).sum()
    assert non_zero > 0, "riverlevel_mean is all-zero through 2024_05 — unexpected"


# ── Seasonal patterns ──────────────────────────────────────────────────────

def test_inundation_only_in_flood_season(master_df):
    """Inundation should only appear in May–September (months 05–09)."""
    non_flood_months = ["01", "02", "03", "04", "10", "11", "12"]
    non_flood = master_df[master_df["timeperiod"].str[-2:].isin(non_flood_months)]
    non_zero = (non_flood["inundation_pct"] > 0).sum()
    assert non_zero == 0, (
        f"inundation_pct is non-zero in {non_zero} non-flood-season rows"
    )


def test_inundation_present_in_peak_flood_months(master_df):
    """June and July should have inundation data for at least some RCs in most years."""
    for year in ["2021", "2022", "2023", "2024", "2025"]:
        for month in ["06", "07"]:
            tp = f"{year}_{month}"
            sub = master_df[master_df["timeperiod"] == tp]
            if sub.empty:
                continue
            non_zero = (sub["inundation_pct"] > 0).sum()
            assert non_zero > 0, (
                f"inundation_pct is all-zero for {tp}, "
                "which is a peak flood month — possible data gap"
            )


def test_rainfall_present_all_months(master_df):
    """IMD rainfall covers the full grid (no all-zero timeperiods)."""
    zero_tps = master_df.groupby("timeperiod")["sum_rain"].apply(
        lambda x: (x == 0).all()
    )
    assert not zero_tps.any(), (
        f"sum_rain is zero for all RCs in: {sorted(zero_tps[zero_tps].index.tolist())}"
    )


# ── Known data issues (asserted as *warnings*, marked xfail) ──────────────

@pytest.mark.xfail(reason="LTIF_tenders_awarded_value is known to be unpopulated")
def test_ltif_not_always_zero(master_df):
    """This will XFAIL until LTIF data is sourced — it documents the gap."""
    non_zero = (master_df["LTIF_tenders_awarded_value"] != 0).sum()
    assert non_zero > 0, "LTIF_tenders_awarded_value is always 0 — data source missing"


@pytest.mark.xfail(reason="Total_House_Fully_Damaged stops after 2023_08 (DRIMS reporting gap)")
def test_house_damage_present_in_2024_floods(master_df):
    """Will XFAIL until DRIMS house-damage field is re-populated for 2024+."""
    flood_2024 = master_df[master_df["timeperiod"].isin(["2024_06", "2024_07", "2024_08"])]
    non_zero = (flood_2024["Total_House_Fully_Damaged"] > 0).sum()
    assert non_zero > 0, "Total_House_Fully_Damaged is 0 through all of 2024 flood season"
