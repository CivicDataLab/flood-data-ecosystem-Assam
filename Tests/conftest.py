"""
Pytest fixtures shared across the test suite.
Constants and utilities live in helpers.py (importable as a regular module).

Run tests from the repo root:
    pytest Tests/
"""
import pandas as pd
import pytest

from helpers import ROOT, SOURCES, skip_if_missing


@pytest.fixture(scope="session")
def master_df():
    """Load MASTER_VARIABLES.csv once per test session."""
    p = SOURCES / "MASTER_VARIABLES.csv"
    skip_if_missing(p)
    return pd.read_csv(p)


@pytest.fixture(scope="session")
def expected_timeperiods():
    """The complete set of YYYY_MM strings the master grid must cover."""
    return sorted(
        pd.date_range(start="2021-04-01", end="2026-05-31", freq="MS")
        .strftime("%Y_%m")
        .tolist()
    )


@pytest.fixture(scope="session")
def expected_object_ids():
    """The 180 revenue-circle object_ids from the canonical GeoJSON."""
    geojson = ROOT / "Maps" / "Geojson" / "assam_rc_2024-11.geojson"
    if not geojson.exists():
        pytest.skip(f"GeoJSON not found: {geojson}")
    import geopandas as gpd
    gdf = gpd.read_file(geojson)
    return sorted(gdf["object_id"].tolist())


@pytest.fixture(scope="session")
def sec_aggregated_dir():
    return SOURCES / "TENDERS" / "data" / "SDRF" / "SEC" / "extracted"


@pytest.fixture(scope="session")
def imd_csv_dir():
    return SOURCES / "IMD" / "data" / "rain" / "csv"


@pytest.fixture(scope="session")
def tender_variable_dir():
    return SOURCES / "TENDERS" / "data" / "variables"
