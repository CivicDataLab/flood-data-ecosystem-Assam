"""
Tests for the SEC PDF extraction pipeline.

Covers:
  1. normalize_district() – OCR noise correction and district name mapping
  2. _parse_same_line()   – amount/district co-extraction with false-positive filters
  3. make_aggregated_df() – per-district aggregation logic
  4. Output aggregated CSVs in Sources/TENDERS/data/SDRF/SEC/extracted/
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

# ── Import the extraction module (safe: has if __name__ == "__main__" guard) ──
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "Sources" / "TENDERS" / "scripts"))

import extract_sec_meetings_39_55 as sec_mod

from helpers import SOURCES, skip_if_missing

EXTRACTED_DIR = SOURCES / "TENDERS" / "data" / "SDRF" / "SEC" / "extracted"

INDIVIDUAL_MEETING_CSVS = [
    "44th_SEC_flood_related_allocations_aggregated.csv",
    "45th_SEC_flood_related_allocations_aggregated.csv",
    "46th_SEC_flood_related_allocations_aggregated.csv",
    "47th_SEC_flood_related_allocations_aggregated.csv",
    "48th_SEC_flood_related_allocations_aggregated.csv",
    "49th_SEC_flood_related_allocations_aggregated.csv",
    "51st_SEC_flood_related_allocations_aggregated.csv",
    "52nd_SEC_flood_related_allocations_aggregated.csv",
    "53rd_SEC_flood_related_allocations_aggregated.csv",
    "54th_SEC_flood_related_allocations_aggregated.csv",
    "55th_SEC_flood_related_allocations_aggregated.csv",
]

AGGREGATED_REQUIRED_COLS = [
    "meeting_no", "date", "district", "source_pdf",
    "total_amount_lakhs", "entries", "fund_types_included",
]


# ── Unit tests: normalize_district ────────────────────────────────────────

class TestNormalizeDistrict:
    def test_clean_known_district(self):
        assert sec_mod.normalize_district("Kamrup") == "Kamrup"

    def test_uppercase_input(self):
        assert sec_mod.normalize_district("DHEMAJI") == "Dhemaji"

    def test_ocr_bongaigaon_split(self):
        assert sec_mod.normalize_district("Bonga Igaon") == "Bongaigaon"

    def test_ocr_sivasagar_to_sivsagar(self):
        result = sec_mod.normalize_district("Sivasagar")
        assert result in ("Sivsagar", "Sivasagar"), (
            f"Expected Sivsagar/Sivasagar, got {result}"
        )

    def test_ocr_k_anglong(self):
        assert sec_mod.normalize_district("K.Anglong") == "Karbi Anglong"

    def test_ocr_kamrup_rural(self):
        assert sec_mod.normalize_district("Kamrup (Rural)") == "Kamrup"

    def test_partial_match_fallback(self):
        """If exact match fails, should still find a valid district."""
        result = sec_mod.normalize_district("Kokrajha R")
        assert result == "Kokrajhar", f"Expected Kokrajhar, got {result}"

    def test_leading_trailing_whitespace(self):
        assert sec_mod.normalize_district("  Nalbari  ") == "Nalbari"


# ── Unit tests: _parse_same_line ──────────────────────────────────────────

class TestParseSameLine:
    """_parse_same_line extracts (district, amount) from lines where both appear."""

    def _run(self, lines, max_amount=5000, min_amount=0.1):
        return sec_mod._parse_same_line(
            lines, annexure="TestAnn", fund_type="SDRF",
            section_no="X.1", meeting_no="Test SEC", date="2022-01-01",
            pdf_name="test.pdf", max_amount=max_amount, min_amount=min_amount,
        )

    def test_extracts_district_and_amount(self):
        rows = self._run(["5 Bongaigaon District Road repair 4.5200"])
        assert len(rows) == 1
        assert rows[0][2] == "Bongaigaon"
        assert rows[0][3] == pytest.approx(4.52)

    def test_skips_chainage_marker(self):
        rows = self._run(["Bongaigaon restoration at Ch.9046.11 m of embankment"])
        assert len(rows) == 0, "Should skip lines with chainage marker"

    def test_skips_total_lines(self):
        rows = self._run(["Kokrajhar Total 2345.67"])
        assert len(rows) == 0, "Should skip lines containing 'total'"

    def test_skips_year_like_amount(self):
        rows = self._run(["Dhemaji flood work 2021.22"])
        assert len(rows) == 0, "Should skip year-like value 2021.22"

    def test_skips_amount_above_max(self):
        rows = self._run(["Kamrup project 50000.00"], max_amount=1000)
        assert len(rows) == 0, "Should skip amounts above max_amount"

    def test_skips_amount_below_min(self):
        rows = self._run(["Nagaon project 0.001"], min_amount=0.1)
        assert len(rows) == 0, "Should skip amounts below min_amount"

    def test_no_match_when_no_district(self):
        rows = self._run(["Road restoration work 14.500"])
        assert len(rows) == 0, "Should skip lines without a recognisable district"

    def test_ocr_district_still_matches(self):
        rows = self._run(["4 Bonga Igaon District TRD restoration 7.50"])
        assert len(rows) == 1
        assert rows[0][2] == "Bongaigaon"


# ── Unit tests: make_aggregated_df ────────────────────────────────────────

class TestMakeAggregatedDf:
    @pytest.fixture
    def sample_itemized(self):
        rows = [
            ["51st SEC", "2024-10-01", "Golaghat", 200.0, "SDMF", "51.7", "Ann III", "desc", "p5", "51st.pdf"],
            ["51st SEC", "2024-10-01", "Golaghat", 100.0, "SDRF", "51.7", "Ann III", "desc", "p6", "51st.pdf"],
            ["51st SEC", "2024-10-01", "Dhemaji",  50.0,  "SDMF", "51.7", "Ann III", "desc", "p7", "51st.pdf"],
        ]
        return sec_mod.make_itemized_df(rows)

    def test_aggregates_same_district(self, sample_itemized):
        agg = sec_mod.make_aggregated_df(sample_itemized)
        golaghat = agg[agg["district"] == "Golaghat"]
        assert len(golaghat) == 1
        assert golaghat["total_amount_lakhs"].iloc[0] == pytest.approx(300.0)

    def test_entry_count(self, sample_itemized):
        agg = sec_mod.make_aggregated_df(sample_itemized)
        golaghat = agg[agg["district"] == "Golaghat"]
        assert golaghat["entries"].iloc[0] == 2

    def test_fund_types_combined(self, sample_itemized):
        agg = sec_mod.make_aggregated_df(sample_itemized)
        golaghat = agg[agg["district"] == "Golaghat"]
        fund_types = golaghat["fund_types_included"].iloc[0]
        assert "SDMF" in fund_types
        assert "SDRF" in fund_types

    def test_separate_districts_not_merged(self, sample_itemized):
        agg = sec_mod.make_aggregated_df(sample_itemized)
        assert len(agg) == 2


# ── Integration tests: aggregated output CSV files ────────────────────────

class TestAggregatedCSVSchema:
    @pytest.mark.parametrize("fname", INDIVIDUAL_MEETING_CSVS)
    def test_schema(self, fname):
        path = EXTRACTED_DIR / fname
        skip_if_missing(path)
        df = pd.read_csv(path)
        for col in AGGREGATED_REQUIRED_COLS:
            assert col in df.columns, f"'{col}' missing in {fname}"

    @pytest.mark.parametrize("fname", INDIVIDUAL_MEETING_CSVS)
    def test_no_negative_amounts(self, fname):
        path = EXTRACTED_DIR / fname
        skip_if_missing(path)
        df = pd.read_csv(path)
        neg = (df["total_amount_lakhs"] < 0).sum()
        assert neg == 0, f"{neg} negative amounts in {fname}"

    @pytest.mark.parametrize("fname", INDIVIDUAL_MEETING_CSVS)
    def test_no_duplicate_districts(self, fname):
        path = EXTRACTED_DIR / fname
        skip_if_missing(path)
        df = pd.read_csv(path)
        dupes = df.duplicated(subset=["meeting_no", "district"]).sum()
        assert dupes == 0, f"{dupes} duplicate (meeting_no, district) rows in {fname}"

    @pytest.mark.parametrize("fname", INDIVIDUAL_MEETING_CSVS)
    def test_entry_count_positive(self, fname):
        path = EXTRACTED_DIR / fname
        skip_if_missing(path)
        df = pd.read_csv(path)
        zero_entries = (df["entries"] <= 0).sum()
        assert zero_entries == 0, f"{zero_entries} rows with zero/negative entries in {fname}"


class TestCombinedAggregatedCSV:
    COMBINED = "44_to_49_and_55th_SEC_flood_related_allocations_aggregated.csv"

    def test_combined_file_exists(self):
        skip_if_missing(EXTRACTED_DIR / self.COMBINED)

    def test_expected_timeperiods_present(self):
        path = EXTRACTED_DIR / self.COMBINED
        skip_if_missing(path)
        df = pd.read_csv(path)
        expected = {"2022_01", "2022_03", "2022_11", "2023_03",
                    "2023_09", "2026_01"}
        actual = set(df["timeperiod"].unique())
        missing = expected - actual
        assert not missing, f"Expected timeperiods missing from combined CSV: {missing}"

    def test_no_assam_aggregate_rows(self):
        path = EXTRACTED_DIR / self.COMBINED
        skip_if_missing(path)
        df = pd.read_csv(path)
        agg_rows = df["District"].str.startswith("Assam", na=False).sum()
        assert agg_rows == 0, (
            f"{agg_rows} state-level aggregate rows found — "
            "these should be excluded from per-district analysis"
        )
