# ### SEC-SDRF procurements
#
# Produces per-revenue-circle SDRF/SDMF sanction values for every SEC meeting
# for which district-level data is available.
#
# Data coverage:
#   44th SEC  – Jan 2022  (2022_01) PWD Roads + Irrigation, extracted from PDF
#   45th SEC  – Mar 2022  (2022_03) WRD + PWD Roads, extracted from PDF
#   46th SEC  – Nov 2022  (2022_11) SDRF tender batch, from 45-50 summary CSV
#   47th SEC  – Feb 2023  (2023_02) No district breakdown – EXCLUDED
#   48th SEC  – Mar 2023  (2023_03) PWD Roads, extracted from PDF
#   49th SEC  – Sep 2023  (2023_09) SDMF + SDRF, extracted from PDF / summary
#   50th SEC  – Mar 2024  (2024_03) SDRF tender batch, from 45-50 summary CSV only
#   51st SEC  – Oct 2024  (2024_10) extracted from PDF
#   52nd SEC  – Feb 2025  (2025_02) extracted from PDF
#   53rd SEC  – Apr 2025  (2025_04) extracted from PDF
#   54th SEC  – Oct 2025  (2025_10) extracted from PDF
#   55th SEC  – Jan 2026  (2026_01) SDMF + SDRF + GR-Flood, extracted from PDF
#
# Meetings 39–43 are fully scanned PDFs; OCR would be needed to extract them.

import glob
import os
import geopandas as gpd
import pandas as pd
from fuzzywuzzy import process

# ──────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────
EXTRACTED    = r'Sources/TENDERS/data/SDRF/SEC/extracted/'
SUMMARY_PATH = r'Sources/TENDERS/data/SDRF/SEC/45th to 50th SEC - Summary.csv'
RC_GDF_PATH  = r'Maps/Geojson/assam_rc_2024-11.geojson'
OUTPUT_DIR   = r'Sources/TENDERS/data/variables/SDRF_sanctions_awarded_value'
SEC_SDRF_OUT = r'Sources/TENDERS/data/SDRF/SEC/SEC_SDRF.csv'


# ──────────────────────────────────────────────
# 1. Load all individual meeting aggregated CSVs
#    (meetings 44–49, 51–55; all share the schema:
#     meeting_no, date, district, source_pdf,
#     total_amount_lakhs, entries, fund_types_included)
# ──────────────────────────────────────────────
# Match only per-meeting files (e.g. "44th_SEC_...", "55th_SEC_...")
# Exclude combined/range files that contain "_to_" in the name
pattern = EXTRACTED + '*_SEC_flood_related_allocations_aggregated.csv'
individual_files = sorted(
    f for f in glob.glob(pattern)
    if '_to_' not in os.path.basename(f)
)

frames = []
for fpath in individual_files:
    df = pd.read_csv(fpath)
    # Normalise the district column name (some files use 'district', some 'District')
    df.columns = [c.strip() for c in df.columns]
    if 'district' in df.columns and 'District' not in df.columns:
        df = df.rename(columns={'district': 'District'})
    # Keep only rows with a real district (exclude state-level aggregates)
    df = df[~df['District'].astype(str).str.startswith('Assam', na=False)]
    # Derive timeperiod from date where missing
    if 'timeperiod' not in df.columns:
        df['timeperiod'] = (
            pd.to_datetime(df['date'], errors='coerce').dt.strftime('%Y_%m')
        )
    # Drop rows where timeperiod or total_amount_lakhs is null
    df = df.dropna(subset=['timeperiod', 'total_amount_lakhs'])
    df = df[df['total_amount_lakhs'] > 0]
    frames.append(df[['District', 'timeperiod', 'total_amount_lakhs']])

all_meetings = pd.concat(frames, ignore_index=True)
# Convert lakhs → rupees to match the rest of the pipeline
all_meetings['SDRF funding'] = all_meetings['total_amount_lakhs'] * 100_000
all_meetings = all_meetings.drop(columns=['total_amount_lakhs'])


# ──────────────────────────────────────────────
# 2. 50th SEC meeting – from the 45-to-50 summary
#    (the 50th meeting PDF was not individually
#     extracted, so the summary is the sole source)
# ──────────────────────────────────────────────
summary_raw = pd.read_csv(SUMMARY_PATH)
summary_raw = summary_raw.rename(columns={'District ': 'District'})

col_50 = '50 SDRF TENDER (lakhs) '   # trailing space is in the original CSV
sdrf_50 = (
    summary_raw[['District', col_50]]
    .rename(columns={col_50: 'SDRF funding'})
    .query('`SDRF funding` > 0')
    .copy()
)
sdrf_50['SDRF funding'] = sdrf_50['SDRF funding'] * 100_000
sdrf_50['timeperiod'] = '2024_03'


# ──────────────────────────────────────────────
# 3. Combine and standardise district names
# ──────────────────────────────────────────────
combined = pd.concat([all_meetings, sdrf_50], ignore_index=True)
combined = combined.dropna(subset=['SDRF funding'])
combined = combined[combined['SDRF funding'] > 0]
combined['District'] = combined['District'].str.lower()


# ──────────────────────────────────────────────
# 4. Fuzzy-merge with revenue-circle GeoJSON
# ──────────────────────────────────────────────
rc_gdf = gpd.read_file(RC_GDF_PATH)


def fuzzy_merge(df_1, df_2, key1, key2, threshold=80, limit=1):
    """Attach the closest matching key from df_2 onto each row of df_1."""
    targets = df_2[key2].tolist()
    df_1 = df_1.copy()
    df_1['matches'] = df_1[key1].apply(
        lambda x: ', '.join(
            m[0] for m in process.extract(x, targets, limit=limit)
            if m[1] >= threshold
        )
    )
    return df_1


fuzzymatch = fuzzy_merge(rc_gdf, combined, 'dtname', 'District', threshold=80, limit=1)

merged = pd.merge(combined, fuzzymatch, left_on='District', right_on='matches')

rc_counts = (
    fuzzymatch.groupby('matches')['revenue_ci']
    .count()
    .reset_index()
    .rename(columns={'revenue_ci': 'num_revenue_circles'})
)
merged = merged.merge(rc_counts, on='matches')

merged['SDRF_RC'] = merged['SDRF funding'] / merged['num_revenue_circles']

drop_cols = [c for c in ['dtname', 'num_revenue_circles', 'geometry', 'HQ', 'revenue_cr']
             if c in merged.columns]
interpolated = merged.drop(columns=drop_cols)
interpolated['District'] = interpolated['District'].str.upper()
interpolated = interpolated.rename(columns={'District': 'DISTRICT'})


# ──────────────────────────────────────────────
# 5. Save outputs
# ──────────────────────────────────────────────
interpolated.to_csv(SEC_SDRF_OUT, index=False)
print(f"Saved full table → {SEC_SDRF_OUT}  ({len(interpolated)} rows)")

os.makedirs(OUTPUT_DIR, exist_ok=True)

for tp in sorted(interpolated['timeperiod'].unique()):
    slice_df = (
        interpolated[interpolated['timeperiod'] == tp][['object_id', 'SDRF_RC']]
        .rename(columns={'SDRF_RC': 'SDRF_sanctions_awarded_value'})
    )
    out_path = os.path.join(OUTPUT_DIR, f"SDRF_sanctions_awarded_value_{tp}.csv")
    slice_df.to_csv(out_path, index=False)
    print(f"  {tp}: {len(slice_df)} revenue circles → {out_path}")
