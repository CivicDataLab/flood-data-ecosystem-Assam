"""
Generic schema and consistency tests that apply across all variable output files.

Tests:
  1. Every per-timeperiod variable CSV must have `object_id` and the variable column.
  2. No duplicate object_ids within a single timeperiod file.
  3. Revenue-circle IDs must be drawn from the canonical 180-RC set.
  4. FFS river-level output: internal consistency (mean in [min, max]).
  5. master2.py assembly logic: merge mechanics tested on synthetic data.
"""
import glob
import re
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "Sources"

from helpers import skip_if_missing

TENDER_VAR_DIR = SOURCES / "TENDERS" / "data" / "variables"
FFS_VAR_DIR    = SOURCES / "FFS" / "data" / "variables"
BHUVAN_VAR_DIR = SOURCES / "BHUVAN" / "data" / "variables"
IMD_CSV_DIR    = SOURCES / "IMD" / "data" / "rain" / "csv"
GEOJSON_PATH   = ROOT / "Maps" / "Geojson" / "assam_rc_2024-11.geojson"

EXPECTED_N_RCS = 180


# ── Helpers ────────────────────────────────────────────────────────────────

def load_canonical_ids():
    if not GEOJSON_PATH.exists():
        return None
    import geopandas as gpd
    gdf = gpd.read_file(GEOJSON_PATH)
    return set(gdf["object_id"].tolist())


# ── Generic per-variable-file checks ──────────────────────────────────────

class TestTenderVariableFileSchema:
    """All variable CSVs under Sources/TENDERS/data/variables/ must conform."""

    def _get_all_csvs(self):
        return list(TENDER_VAR_DIR.glob("**/*.csv")) if TENDER_VAR_DIR.exists() else []

    def test_all_have_object_id(self):
        skip_if_missing(TENDER_VAR_DIR)
        bad_files = []
        for csv in self._get_all_csvs():
            df = pd.read_csv(csv, nrows=1)
            if "object_id" not in df.columns:
                bad_files.append(csv.name)
        assert not bad_files, f"Files missing object_id column: {bad_files[:5]}"

    def test_no_duplicate_object_ids_per_file(self):
        skip_if_missing(TENDER_VAR_DIR)
        bad_files = []
        for csv in sorted(self._get_all_csvs())[:50]:  # sample
            df = pd.read_csv(csv)
            if "object_id" in df.columns and df["object_id"].duplicated().any():
                bad_files.append(csv.name)
        assert not bad_files, f"Duplicate object_ids in: {bad_files[:5]}"

    def test_object_ids_within_canonical_set(self):
        canonical = load_canonical_ids()
        if canonical is None:
            pytest.skip("GeoJSON not found; cannot check canonical object_ids")
        skip_if_missing(TENDER_VAR_DIR)
        bad = []
        for csv in sorted(self._get_all_csvs())[:20]:
            df = pd.read_csv(csv)
            if "object_id" not in df.columns:
                continue
            outliers = set(df["object_id"].unique()) - canonical
            if outliers:
                bad.append((csv.name, list(outliers)[:3]))
        assert not bad, f"Files with object_ids outside canonical 180-RC set: {bad[:3]}"

    def test_filename_contains_timeperiod(self):
        skip_if_missing(TENDER_VAR_DIR)
        bad = []
        for csv in self._get_all_csvs():
            if not re.search(r"\d{4}_\d{2}", csv.stem):
                bad.append(csv.name)
        assert not bad, f"Files without YYYY_MM in name: {bad[:5]}"


# ── FFS river-level variable files ────────────────────────────────────────

class TestFFSRiverLevelFiles:
    RIVERLEVEL_CSV = SOURCES / "master" / "riverlevel.csv"

    def test_riverlevel_file_exists(self):
        skip_if_missing(self.RIVERLEVEL_CSV)

    def _load_clean(self):
        """Load riverlevel.csv, drop any repeated-header rows from append mode."""
        df = pd.read_csv(self.RIVERLEVEL_CSV)
        # Drop rows where the timeperiod column contains the literal string "timeperiod"
        # (an artefact of FFS transformer.py using mode='a' without header=False)
        df = df[df["timeperiod"] != "timeperiod"].copy()
        for col in ["riverlevel_mean", "riverlevel_min", "riverlevel_max"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df

    def test_riverlevel_schema(self):
        skip_if_missing(self.RIVERLEVEL_CSV)
        df = self._load_clean()
        # Column name varies: older builds use 'objectid', newer use 'object_id'
        has_id = "object_id" in df.columns or "objectid" in df.columns
        assert has_id, "Neither 'object_id' nor 'objectid' found in riverlevel.csv"
        for col in ["timeperiod", "riverlevel_mean", "riverlevel_min", "riverlevel_max"]:
            assert col in df.columns, f"'{col}' missing from riverlevel.csv"

    def test_riverlevel_mean_between_min_max(self):
        skip_if_missing(self.RIVERLEVEL_CSV)
        df = self._load_clean().dropna(subset=["riverlevel_mean", "riverlevel_max", "riverlevel_min"])
        above = (df["riverlevel_mean"] > df["riverlevel_max"] + 1e-3).sum()
        below = (df["riverlevel_mean"] < df["riverlevel_min"] - 1e-3).sum()
        assert above == 0, f"{above} rows where mean > max in riverlevel.csv"
        assert below == 0, f"{below} rows where mean < min in riverlevel.csv"

    @pytest.mark.xfail(
        reason="Known FFS data issue: RC 18-316-00185 has riverlevel_min=-2.0 "
               "in 2018_05 — likely a sensor error. Fix in FFS/scripts/transformer.py."
    )
    def test_riverlevel_non_negative(self):
        skip_if_missing(self.RIVERLEVEL_CSV)
        df = self._load_clean().dropna(subset=["riverlevel_mean"])
        for col in ["riverlevel_mean", "riverlevel_min", "riverlevel_max"]:
            if col in df.columns:
                neg = (pd.to_numeric(df[col], errors="coerce") < 0).sum()
                assert neg == 0, f"{neg} negative values in '{col}'"

    def test_riverlevel_timeperiod_format(self):
        skip_if_missing(self.RIVERLEVEL_CSV)
        df = self._load_clean()
        bad = df[~df["timeperiod"].str.match(r"^\d{4}_\d{2}$", na=False)]
        assert bad.empty, f"Bad timeperiod values: {bad['timeperiod'].unique()[:5]}"


# ── Inundation variable files (Bhuvan) ────────────────────────────────────

class TestBhuvanInundationFiles:
    INUNDATION_DIR = BHUVAN_VAR_DIR / "inundation_pct" if BHUVAN_VAR_DIR.exists() else None

    def test_inundation_dir_check(self):
        if self.INUNDATION_DIR is None:
            pytest.skip("BHUVAN data directory not found")
        skip_if_missing(self.INUNDATION_DIR)

    def test_inundation_schema(self):
        if self.INUNDATION_DIR is None:
            pytest.skip("BHUVAN data directory not found")
        skip_if_missing(self.INUNDATION_DIR)
        for csv in sorted(self.INUNDATION_DIR.glob("*.csv"))[:5]:
            df = pd.read_csv(csv)
            assert "object_id" in df.columns, f"No object_id in {csv.name}"
            assert "inundation_pct" in df.columns, f"No inundation_pct in {csv.name}"

    def test_inundation_pct_range(self):
        if self.INUNDATION_DIR is None:
            pytest.skip("BHUVAN data directory not found")
        skip_if_missing(self.INUNDATION_DIR)
        for csv in self.INUNDATION_DIR.glob("*.csv"):
            df = pd.read_csv(csv)
            if "inundation_pct" in df.columns:
                over_100 = (df["inundation_pct"] > 100).sum()
                assert over_100 == 0, (
                    f"{over_100} inundation_pct > 100 in {csv.name}"
                )
                neg = (df["inundation_pct"] < 0).sum()
                assert neg == 0, f"{neg} negative inundation_pct in {csv.name}"


# ── master2.py assembly logic ─────────────────────────────────────────────

class TestMasterAssemblyLogic:
    """Test the merge / imputation logic from master2.py on synthetic data."""

    @pytest.fixture
    def base_grid(self):
        """Minimal RC × timeperiod grid as produced by master2.py."""
        return pd.DataFrame({
            "object_id": ["RC-001", "RC-001", "RC-002", "RC-002"],
            "district":  ["Dist A", "Dist A", "Dist B", "Dist B"],
            "timeperiod": ["2023_06", "2023_07", "2023_06", "2023_07"],
        })

    @pytest.fixture
    def variable_df(self):
        return pd.DataFrame({
            "object_id":                  ["RC-001", "RC-002"],
            "timeperiod":                 ["2023_06", "2023_06"],
            "total_tender_awarded_value": [1000.0,   2000.0],
        })

    def test_left_merge_preserves_all_rows(self, base_grid, variable_df):
        result = base_grid.merge(variable_df, on=["object_id", "timeperiod"], how="left")
        assert len(result) == len(base_grid)

    def test_missing_values_filled_with_zero(self, base_grid, variable_df):
        result = base_grid.merge(variable_df, on=["object_id", "timeperiod"], how="left")
        result = result.fillna(0)
        assert result["total_tender_awarded_value"].isna().sum() == 0

    def test_no_row_multiplication_on_merge(self, base_grid, variable_df):
        """A many-to-one merge must not multiply rows."""
        result = base_grid.merge(variable_df, on=["object_id", "timeperiod"], how="left")
        assert len(result) == len(base_grid), (
            "Row count changed after merge — possible many-to-many join"
        )

    def test_duplicate_column_suffix_cleanup(self, base_grid):
        """Replicate master2.py _x/_y suffix cleanup logic."""
        extra_col = base_grid.copy()
        extra_col["district_x"] = "A"
        extra_col["district_y"] = "B"
        cleaned = extra_col.drop(
            columns=extra_col.filter(regex="_x$|_y$").columns
        )
        assert "district_x" not in cleaned.columns
        assert "district_y" not in cleaned.columns

    def test_annual_variable_broadcast_to_monthly(self):
        """Annual WorldPop data should broadcast to 12 monthly rows per RC."""
        monthly = pd.DataFrame({
            "object_id":  ["RC-001"] * 12,
            "timeperiod": [f"2023_{m:02d}" for m in range(1, 13)],
        })
        monthly["year"] = monthly["timeperiod"].str[:4].astype(int)

        annual = pd.DataFrame({
            "object_id":      ["RC-001"],
            "year":           [2023],
            "sum_population": [100_000.0],
        })

        result = monthly.merge(annual, on=["object_id", "year"], how="left")
        assert len(result) == 12
        assert (result["sum_population"] == 100_000.0).all()

    def test_rainfall_imputation_by_rc_mean(self):
        """NaN rainfall values should be filled with the RC-level mean."""
        df = pd.DataFrame({
            "object_id": ["RC-001", "RC-001", "RC-001"],
            "timeperiod": ["2023_06", "2023_07", "2023_08"],
            "sum_rain":   [50.0, float("nan"), 70.0],
        })
        df["sum_rain"] = df["sum_rain"].fillna(
            df.groupby("object_id")["sum_rain"].transform("mean")
        )
        assert df["sum_rain"].isna().sum() == 0
        assert df.loc[1, "sum_rain"] == pytest.approx(60.0)

    def test_ndvi_forward_fill(self):
        """NDVI gaps must be filled by forward-fill within each RC."""
        df = pd.DataFrame({
            "object_id": ["RC-001", "RC-001", "RC-001"],
            "timeperiod": ["2023_06", "2023_07", "2023_08"],
            "mean_ndvi":  [0.5, float("nan"), float("nan")],
        })
        df = df.sort_values(["object_id", "timeperiod"])
        df["mean_ndvi"] = df["mean_ndvi"].ffill()
        assert (df["mean_ndvi"] == 0.5).all()
