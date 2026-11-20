"""
Assam – WorldPop age-sex stats per revenue circle.

Adds to worldpopstats_<year>.csv:
  mean_sex_ratio, sum_aged_population, sum_young_population,
  sum_female_population, sum_male_population

Run from repo root:
  python worldpop_agesex_stats_assam.py
"""
import re
from pathlib import Path
import pandas as pd

# -------------------------------------------------------------------
# CONFIG
# -------------------------------------------------------------------
worldpop_dir = Path.cwd() / "Sources" / "WORLDPOP" / "data"
demographic_dir = worldpop_dir / "agesexstructure"  # <year>/<object_id>_agesexpyramid_<year>.csv
output_dir = worldpop_dir

NAME_COL = "revenue_cr"          # revenue circle name column
YEARS = [2017, 2018, 2019, 2020]

AGED_CLASSES = [65, 70, 75, 80]
YOUNG_CLASSES = [0, 1]

STAT_COLS = [
    "mean_sex_ratio",
    "sum_aged_population",
    "sum_young_population",
    "sum_female_population",
    "sum_male_population",
]


# -------------------------------------------------------------------
# FUNCTIONS
# -------------------------------------------------------------------
def calculate_population_statistics(demographic_file: Path) -> dict:
    df = pd.read_csv(demographic_file)

    total_male = df["male"].sum()
    total_female = df["female"].sum()

    return {
        "mean_sex_ratio": total_female / total_male if total_male > 0 else 0,  # F/M, e.g. 0.93
        "sum_aged_population": df.loc[df["class"].isin(AGED_CLASSES), ["male", "female"]].sum().sum(),
        "sum_young_population": df.loc[df["class"].isin(YOUNG_CLASSES), ["male", "female"]].sum().sum(),
        "sum_female_population": total_female,
        "sum_male_population": total_male,
    }


def normalize_name(name) -> str:
    name = str(name).replace("-", " ")
    name = re.sub(r"\s+", " ", name.strip())   # also fixes "Bongaigaon\n(Pt)"
    return name.replace(" ", "_").upper()


def process_yearly_data(year: int):
    worldpop_file = worldpop_dir / f"worldpopstats_{year}.csv"
    if not worldpop_file.exists():
        print(f"WorldPop file not found for {year}: {worldpop_file}")
        return

    print(f"\nProcessing {year}: {worldpop_file}")
    worldpop_df = pd.read_csv(worldpop_file)

    missing = [c for c in ["object_id", NAME_COL] if c not in worldpop_df.columns]
    if missing:
        raise KeyError(f"Missing columns in {worldpop_file}: {missing}")

    # Drop old stat columns + any _x/_y/_dem leftovers so re-runs stay clean
    stale = [
        c for c in worldpop_df.columns
        if c in STAT_COLS
        or any(c == f"{s}{suf}" for s in STAT_COLS for suf in ("_x", "_y", "_dem"))
    ]
    worldpop_df = worldpop_df.drop(columns=stale)

    worldpop_df["subdistrict_name_norm"] = worldpop_df[NAME_COL].apply(normalize_name)

    year_dir = demographic_dir / str(year)
    if not year_dir.exists():
        print(f"Demographic folder not found: {year_dir}")

    rows, n_missing = [], 0
    for object_id in worldpop_df["object_id"].unique():
        f = year_dir / f"{year}_{object_id}.csv"
        if f.exists():
            stats = calculate_population_statistics(f)
        else:
            print(f"  missing: {f.name}")
            stats = {c: None for c in STAT_COLS}
            n_missing += 1
        rows.append({"object_id": object_id, **stats})

    out_df = worldpop_df.merge(pd.DataFrame(rows), on="object_id", how="left")

    out = output_dir / f"worldpopstats_{year}.csv"
    out_df.to_csv(out, index=False)

    fem = out_df["sum_female_population"].sum()
    tot = out_df["sum_population"].sum() if "sum_population" in out_df else float("nan")
    print(f"Saved {out}")
    print(f"  circles: {len(out_df)} | missing pyramids: {n_missing}")
    print(f"  female pop: {fem:,.0f} | sum_population: {tot:,.0f} | female share: {fem / tot:.3f}")


# -------------------------------------------------------------------
if __name__ == "__main__":
    for y in YEARS:
        process_yearly_data(y)