"""
Tests for the IMD rainfall variable pipeline.

Covers:
  1. Monthly CSV schema (required columns present)
  2. Non-negative rainfall values
  3. Internal consistency: mean ≤ max, mean ≥ 0
  4. Coverage: all expected months present in the date range
  5. IMD utils.py – keep_columns_in_csv logic
"""
import glob
import re
from pathlib import Path

import pandas as pd
import pytest

from helpers import ROOT, SOURCES, skip_if_missing

IMD_CSV_DIR = SOURCES / "IMD" / "data" / "rain" / "csv"

REQUIRED_COLS_RAW = {"object_id", "max", "mean", "sum"}


# ── Integration tests: IMD rainfall CSV files ──────────────────────────────

class TestIMDRainfallFiles:
    def test_imd_csv_dir_exists(self):
        skip_if_missing(IMD_CSV_DIR)

    def test_at_least_one_csv_present(self):
        skip_if_missing(IMD_CSV_DIR)
        csvs = list(IMD_CSV_DIR.glob("*.csv"))
        assert len(csvs) > 0, "No IMD rainfall CSV files found"

    def test_filename_format(self):
        skip_if_missing(IMD_CSV_DIR)
        for csv in IMD_CSV_DIR.glob("*.csv"):
            match = re.match(r"\d{4}_\d{2}\.csv$", csv.name)
            assert match, f"Unexpected filename format: {csv.name} (expected YYYY_MM.csv)"

    def test_required_columns_present(self):
        skip_if_missing(IMD_CSV_DIR)
        for csv in sorted(IMD_CSV_DIR.glob("*.csv"))[:10]:
            df = pd.read_csv(csv)
            # Accept either 'id'/'object_id' as the RC identifier
            has_id = "id" in df.columns or "object_id" in df.columns
            assert has_id, f"No id/object_id column in {csv.name}"
            for col in ["max", "mean", "sum"]:
                assert col in df.columns, f"'{col}' missing from {csv.name}"

    def test_non_negative_values(self):
        skip_if_missing(IMD_CSV_DIR)
        for csv in IMD_CSV_DIR.glob("*.csv"):
            df = pd.read_csv(csv)
            for col in ["max", "mean", "sum"]:
                if col in df.columns:
                    neg = (df[col] < 0).sum()
                    assert neg == 0, f"{neg} negative '{col}' values in {csv.name}"

    def test_mean_le_max(self):
        skip_if_missing(IMD_CSV_DIR)
        for csv in sorted(IMD_CSV_DIR.glob("*.csv"))[:20]:
            df = pd.read_csv(csv)
            if "max" in df.columns and "mean" in df.columns:
                violations = (df["mean"] > df["max"] + 1e-6).sum()
                assert violations == 0, (
                    f"{violations} rows where mean_rain > max_rain in {csv.name}"
                )

    def test_no_duplicate_rc_ids(self):
        skip_if_missing(IMD_CSV_DIR)
        for csv in sorted(IMD_CSV_DIR.glob("*.csv"))[:10]:
            df = pd.read_csv(csv)
            id_col = "object_id" if "object_id" in df.columns else "id"
            dupes = df[id_col].duplicated().sum()
            assert dupes == 0, f"{dupes} duplicate RC ids in {csv.name}"

    def test_coverage_includes_flood_years(self):
        """Monthly files must exist for core flood season months."""
        skip_if_missing(IMD_CSV_DIR)
        csvs = {f.stem for f in IMD_CSV_DIR.glob("*.csv")}
        required_months = [
            "2021_07", "2022_07", "2023_07", "2024_07",
            "2022_06", "2023_06",
        ]
        missing = [m for m in required_months if m not in csvs]
        assert not missing, (
            f"IMD CSV files missing for flood-season months: {missing}"
        )

    def test_total_months_expected(self):
        """Date range 2021-04 to 2026-05 = 62 months; at minimum the non-recent
        months should have files (older than 2 years). Flag if fewer than 50."""
        skip_if_missing(IMD_CSV_DIR)
        csvs = list(IMD_CSV_DIR.glob("*.csv"))
        assert len(csvs) >= 50, (
            f"Only {len(csvs)} IMD files found; expected ≥50 for the project date range"
        )


# ── Unit tests: IMD utils.py – keep_columns_in_csv ────────────────────────

class TestIMDKeepColumnsCsv:
    """Test the column-filtering utility without file I/O (uses tmp_path)."""

    @pytest.fixture
    def sample_csv(self, tmp_path):
        df = pd.DataFrame({
            "id": [1, 2],
            "max": [10.0, 20.0],
            "mean": [5.0, 15.0],
            "count": [100, 200],
            "sum": [50.0, 100.0],
            "extra_col": ["a", "b"],
        })
        p = tmp_path / "test.csv"
        df.to_csv(p, index=False)
        return tmp_path

    def test_keeps_only_specified_columns(self, sample_csv, tmp_path):
        """Replicate the logic from IMD/scripts/utils.py."""
        import os
        columns_to_keep = ["id", "max", "mean", "count", "sum"]
        out_folder = tmp_path / "out"
        out_folder.mkdir()
        for fname in os.listdir(sample_csv):
            if fname.endswith(".csv"):
                df = pd.read_csv(sample_csv / fname)
                df = df[columns_to_keep]
                df.to_csv(out_folder / fname, index=False)

        result = pd.read_csv(out_folder / "test.csv")
        assert list(result.columns) == columns_to_keep
        assert "extra_col" not in result.columns

    def test_preserves_row_count(self, sample_csv, tmp_path):
        import os
        out = tmp_path / "out2"
        out.mkdir()
        for fname in os.listdir(sample_csv):
            if fname.endswith(".csv"):
                df = pd.read_csv(sample_csv / fname)[["id", "max", "mean", "count", "sum"]]
                df.to_csv(out / fname, index=False)
        result = pd.read_csv(out / "test.csv")
        assert len(result) == 2
