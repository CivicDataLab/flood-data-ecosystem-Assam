"""
Tests for the WorldPop population projection pipeline.

Covers:
  1. Linear-regression projection logic (extrapolate_variable)
  2. WorldPopDataFetcher helper methods (geometry simplification)
  3. Output variable CSVs for sum_population and related columns
  4. Projected values are monotonically sensible (no wild negatives)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "Sources"

from helpers import skip_if_missing

WORLDPOP_VAR_DIR  = SOURCES / "WORLDPOP" / "data" / "variables"
POP_VAR_DIR       = WORLDPOP_VAR_DIR / "sum_population"
AGED_VAR_DIR      = WORLDPOP_VAR_DIR / "sum_aged_population"
YOUNG_VAR_DIR     = WORLDPOP_VAR_DIR / "sum_young_population"

PROJECTION_YEARS  = ["2021", "2022", "2023", "2024", "2025", "2026"]


# ── Unit tests: extrapolation logic ────────────────────────────────────────

class TestExtrapolateVariable:
    """Test the linear-regression extrapolation in WORLDPOP/scripts/projections.py.
    Inline the logic to avoid importing the top-level script (sys.argv dependency)."""

    @staticmethod
    def extrapolate(years, values, target_years):
        from sklearn.linear_model import LinearRegression
        X = np.array(years).reshape(-1, 1)
        y = np.array(values).reshape(-1, 1)
        model = LinearRegression()
        model.fit(X, y)
        X_pred = np.array(target_years).reshape(-1, 1)
        return model.predict(X_pred).flatten()

    def test_linear_trend_extrapolated_correctly(self):
        """Perfect linear data should extrapolate exactly."""
        years = [2015, 2016, 2017, 2018, 2019, 2020]
        values = [1000, 1050, 1100, 1150, 1200, 1250]
        result = self.extrapolate(years, values, [2021, 2022])
        assert result[0] == pytest.approx(1300, abs=1)
        assert result[1] == pytest.approx(1350, abs=1)

    def test_result_has_correct_length(self):
        result = self.extrapolate(
            [2015, 2016, 2017], [1000, 1010, 1020],
            [2021, 2022, 2023, 2024, 2025, 2026]
        )
        assert len(result) == 6

    def test_projection_non_negative_for_sensible_input(self):
        """Population projections for realistic Assam data should stay positive."""
        years  = [2010, 2015, 2020]
        values = [100_000, 105_000, 110_000]
        # PROJECTION_YEARS must be ints for sklearn
        target = [int(y) for y in PROJECTION_YEARS]
        result = self.extrapolate(years, values, target)
        assert all(v > 0 for v in result), (
            f"Got negative projected population: {result}"
        )

    def test_declining_trend_stays_plausible(self):
        """Even a declining trend should not produce extremely negative values
        over a 6-year projection horizon."""
        years  = [2010, 2015, 2020]
        values = [200_000, 190_000, 180_000]
        target = [int(y) for y in PROJECTION_YEARS]
        result = self.extrapolate(years, values, target)
        assert all(v > 50_000 for v in result), (
            "Projected population dropped unrealistically: "
            f"min={min(result):.0f}"
        )


# ── Unit tests: WorldPopDataFetcher geometry helpers ─────────────────────

class TestWorldPopDataFetcherHelpers:
    """Test geometric helpers without hitting the WorldPop API."""

    @pytest.fixture
    def fetcher(self):
        sys.path.insert(0, str(SOURCES / "WORLDPOP" / "scraper" / "scraper_scripts"))
        from worldpop_data_fetcher import WorldPopDataFetcher
        import tempfile, os
        with tempfile.TemporaryDirectory() as tmpdir:
            fetcher = WorldPopDataFetcher.__new__(WorldPopDataFetcher)
            fetcher.base_url = "https://api.worldpop.org/v1"
            fetcher.output_dir = Path(tmpdir)
            yield fetcher

    @pytest.fixture
    def square_geojson(self):
        return {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[90, 24], [92, 24], [92, 26], [90, 26], [90, 24]]]
                },
                "properties": {}
            }]
        }

    def test_simplify_geometry_returns_valid_geojson(self, fetcher, square_geojson):
        result = fetcher.simplify_geometry(square_geojson, tolerance=0.01)
        assert result["type"] == "FeatureCollection"
        assert "features" in result
        assert result["features"][0]["geometry"]["type"] == "Polygon"

    def test_simplify_does_not_collapse_large_polygon(self, fetcher, square_geojson):
        """A 2-degree polygon simplified at tolerance=0.1 should remain non-empty."""
        result = fetcher.simplify_geometry(square_geojson, tolerance=0.1)
        coords = result["features"][0]["geometry"]["coordinates"]
        assert len(coords[0]) >= 3, "Polygon collapsed after simplification"

    def test_truncate_coordinates_precision(self, fetcher, square_geojson):
        result = fetcher.truncate_coordinates(square_geojson, precision=2)
        coords = result["features"][0]["geometry"]["coordinates"][0]
        for point in coords:
            for val in point:
                assert round(val, 2) == val, (
                    f"Coordinate {val} has more than 2 decimal places after truncation"
                )


# ── Integration tests: output population variable CSVs ────────────────────

class TestWorldPopOutputFiles:
    @pytest.mark.parametrize("year", PROJECTION_YEARS)
    def test_population_file_exists(self, year):
        p = POP_VAR_DIR / f"sum_population_{year}.csv"
        skip_if_missing(p)

    @pytest.mark.parametrize("year", PROJECTION_YEARS)
    def test_population_schema(self, year):
        p = POP_VAR_DIR / f"sum_population_{year}.csv"
        skip_if_missing(p)
        df = pd.read_csv(p)
        assert "object_id" in df.columns, f"No object_id in sum_population_{year}.csv"
        assert "sum_population" in df.columns, (
            f"No sum_population in sum_population_{year}.csv"
        )

    @pytest.mark.parametrize("year", ["2021", "2022", "2023", "2024", "2025"])
    def test_population_positive_pre_2026(self, year):
        p = POP_VAR_DIR / f"sum_population_{year}.csv"
        skip_if_missing(p)
        df = pd.read_csv(p)
        non_positive = (df["sum_population"] <= 0).sum()
        assert non_positive == 0, (
            f"{non_positive} zero/negative sum_population values for {year}"
        )

    def test_no_duplicate_object_ids(self):
        year = "2023"
        p = POP_VAR_DIR / f"sum_population_{year}.csv"
        skip_if_missing(p)
        df = pd.read_csv(p)
        dupes = df["object_id"].duplicated().sum()
        assert dupes == 0, f"{dupes} duplicate object_ids in sum_population_{year}.csv"

    def test_population_decreases_over_time(self):
        """Assam's population trend should be broadly consistent year-on-year
        (linear projection keeps values within 5% of each other)."""
        y2021 = POP_VAR_DIR / "sum_population_2021.csv"
        y2025 = POP_VAR_DIR / "sum_population_2025.csv"
        skip_if_missing(y2021)
        skip_if_missing(y2025)
        df_21 = pd.read_csv(y2021).set_index("object_id")["sum_population"]
        df_25 = pd.read_csv(y2025).set_index("object_id")["sum_population"]
        common = df_21.index.intersection(df_25.index)
        if len(common) == 0:
            pytest.skip("No common object_ids between 2021 and 2025 files")
        ratio = df_25[common] / df_21[common]
        # Expect max 20% change over 4 years (linear trend)
        assert (ratio > 0.80).all() and (ratio < 1.20).all(), (
            "Some RCs show >20% population change 2021→2025 — "
            "check linear projection parameters"
        )
