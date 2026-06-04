"""
Tests for the tender data pipeline.

Covers:
  1. flood_filter() – keyword-based flood/non-flood classification
  2. Awarded-value parsing (comma removal → float)
  3. Output variable CSVs from Sources/TENDERS/data/variables/
  4. SEC procurement pipeline (SEC-SDRF_procurements.py outputs)
"""
import glob
import re

import pandas as pd
import pytest

from helpers import ROOT, SOURCES, skip_if_missing

TENDER_VAR_DIR = SOURCES / "TENDERS" / "data" / "variables"
SDRF_SANCTION_DIR = TENDER_VAR_DIR / "SDRF_sanctions_awarded_value"
TOTAL_TENDER_DIR  = TENDER_VAR_DIR / "total_tender_awarded_value"

# ── Inline flood-filter logic (mirrors Sources/TENDERS/scripts/flood_tenders.py)
# Cannot import directly because the script has top-level side-effects.
POSITIVE_KEYWORDS = [
    "Flood", "Embankment", "embkt", "Relief", "Erosion", "SDRF",
    "Inundation", "Hydrology", "Silt", "Siltation", "Bund", "Trench",
    "Breach", "Culvert", "Sluice", "Dyke",
    "Storm water drain", "Emergency", "Immediate", "IM", "AE", "A E",
    "AAPDA MITRA",
]
NEGATIVE_KEYWORDS = ["Floodlight", "Flood Light", "GAS", "FIFA", "pipe", "pipes", "covid"]


def flood_filter(ref: str, title: str, description: str):
    """Classify a single tender as flood-related or not."""
    slug = f"{ref} {title} {description}"
    slug = re.sub(r"[^a-zA-Z0-9 \n\.]", " ", slug)

    is_flood = False
    for kw in POSITIVE_KEYWORDS:
        if re.search(r"\b%s\b" % re.escape(kw.lower()), slug.lower()):
            is_flood = True
            break
    for kw in NEGATIVE_KEYWORDS:
        if re.search(r"\b%s\b" % re.escape(kw.lower()), slug.lower()):
            is_flood = False
            break
    return is_flood


def parse_awarded_value(raw: str) -> float:
    return float(str(raw).replace(",", ""))


# ── Unit tests: flood_filter ───────────────────────────────────────────────

class TestFloodFilter:
    def test_flood_keyword_positive(self):
        assert flood_filter("T001", "Flood restoration work", "") is True

    def test_embankment_keyword_positive(self):
        assert flood_filter("T002", "Embankment repair at Majuli", "") is True

    def test_erosion_keyword_positive(self):
        assert flood_filter("T003", "Erosion protection works", "") is True

    def test_sdrf_keyword_positive(self):
        assert flood_filter("T004", "Work under SDRF scheme", "") is True

    def test_immediate_keyword_positive(self):
        assert flood_filter("T005", "Immediate restoration of road", "") is True

    def test_breach_keyword_positive(self):
        assert flood_filter("T006", "", "Breach closing at Dhubri bund") is True

    def test_culvert_keyword_positive(self):
        assert flood_filter("T007", "Culvert repair", "") is True

    def test_negative_override_floodlight(self):
        """Floodlight cancels the Flood hit."""
        assert flood_filter("T008", "Installation of Floodlight at stadium", "") is False

    def test_negative_override_pipe(self):
        """pipe cancels Relief."""
        assert flood_filter("T009", "Supply of Relief materials for pipes", "") is False

    def test_negative_override_gas(self):
        assert flood_filter("T010", "Flood-related GAS supply tender", "") is False

    def test_unrelated_tender(self):
        assert flood_filter("T011", "Construction of school building", "") is False

    def test_case_insensitive_match(self):
        assert flood_filter("T012", "FLOOD PROTECTION WORKS", "") is True

    def test_keyword_in_description_field(self):
        assert flood_filter("T013", "Road restoration", "under SDRF guidelines") is True

    def test_embkt_abbreviation(self):
        assert flood_filter("T014", "embkt protection spur", "") is True

    def test_dyke_keyword(self):
        assert flood_filter("T015", "Repair of dyke at Sonitpur", "") is True


# ── Unit tests: awarded-value parsing ──────────────────────────────────────

class TestAwardedValueParsing:
    def test_plain_number(self):
        assert parse_awarded_value("123456.78") == pytest.approx(123456.78)

    def test_indian_comma_format(self):
        assert parse_awarded_value("1,23,45,678") == pytest.approx(12345678.0)

    def test_already_float(self):
        assert parse_awarded_value(9999.0) == pytest.approx(9999.0)

    def test_zero(self):
        assert parse_awarded_value("0") == 0.0


# ── Integration tests: output variable CSV files ───────────────────────────

class TestTenderVariableFiles:
    def test_tender_variable_dir_exists(self, tender_variable_dir):
        assert tender_variable_dir.exists(), (
            f"Variable output directory missing: {tender_variable_dir}"
        )

    def test_total_tender_files_exist(self):
        skip_if_missing(TOTAL_TENDER_DIR)
        csvs = list(TOTAL_TENDER_DIR.glob("*.csv"))
        assert len(csvs) > 0, "No total_tender_awarded_value CSVs found"

    def test_total_tender_file_schema(self):
        skip_if_missing(TOTAL_TENDER_DIR)
        for csv in sorted(TOTAL_TENDER_DIR.glob("*.csv"))[:5]:
            df = pd.read_csv(csv)
            assert "object_id" in df.columns, f"No object_id in {csv.name}"
            assert "total_tender_awarded_value" in df.columns, (
                f"No total_tender_awarded_value in {csv.name}"
            )

    def test_total_tender_values_non_negative(self):
        skip_if_missing(TOTAL_TENDER_DIR)
        for csv in TOTAL_TENDER_DIR.glob("*.csv"):
            df = pd.read_csv(csv)
            assert (df["total_tender_awarded_value"] >= 0).all(), (
                f"Negative tender values in {csv.name}"
            )

    def test_total_tender_no_duplicate_object_ids(self):
        skip_if_missing(TOTAL_TENDER_DIR)
        for csv in sorted(TOTAL_TENDER_DIR.glob("*.csv"))[:10]:
            df = pd.read_csv(csv)
            dupes = df["object_id"].duplicated().sum()
            assert dupes == 0, f"{dupes} duplicate object_ids in {csv.name}"

    def test_total_tender_filename_timeperiod_format(self):
        skip_if_missing(TOTAL_TENDER_DIR)
        for csv in TOTAL_TENDER_DIR.glob("*.csv"):
            match = re.search(r"\d{4}_\d{2}", csv.stem)
            assert match, f"Cannot parse YYYY_MM from filename: {csv.name}"


class TestSDRFSanctionFiles:
    def test_sdrf_sanction_dir_exists(self):
        skip_if_missing(SDRF_SANCTION_DIR)

    def test_sdrf_sanction_file_schema(self):
        skip_if_missing(SDRF_SANCTION_DIR)
        for csv in sorted(SDRF_SANCTION_DIR.glob("*.csv"))[:5]:
            df = pd.read_csv(csv)
            assert "object_id" in df.columns, f"No object_id in {csv.name}"
            assert "SDRF_sanctions_awarded_value" in df.columns, (
                f"No SDRF_sanctions_awarded_value in {csv.name}"
            )

    def test_sdrf_sanction_values_non_negative(self):
        skip_if_missing(SDRF_SANCTION_DIR)
        for csv in SDRF_SANCTION_DIR.glob("*.csv"):
            df = pd.read_csv(csv)
            neg = (df["SDRF_sanctions_awarded_value"] < 0).sum()
            assert neg == 0, f"{neg} negative SDRF sanction values in {csv.name}"

    def test_expected_timeperiods_covered(self):
        """Meetings 44–55 should produce files for their respective timeperiods."""
        skip_if_missing(SDRF_SANCTION_DIR)
        expected_tps = [
            "2022_01", "2022_03", "2022_11",
            "2023_03", "2023_09", "2024_03",
            "2024_10", "2025_02", "2025_04", "2025_10", "2026_01",
        ]
        existing_files = {f.stem.replace("SDRF_sanctions_awarded_value_", "")
                         for f in SDRF_SANCTION_DIR.glob("*.csv")}
        missing = [tp for tp in expected_tps if tp not in existing_files]
        assert not missing, (
            f"Missing SDRF sanction files for timeperiods: {missing}. "
            "Re-run Sources/TENDERS/scripts/SEC-SDRF_procurements.py"
        )
