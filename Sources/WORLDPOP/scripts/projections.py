import glob
import os
import sys

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

path = os.getcwd() + "/Sources/WORLDPOP/"

if len(sys.argv) < 2:
    sys.exit("Usage: python Sources/WORLDPOP/scripts/projections.py <variable>  e.g. sum_female_population")
projected_variable = sys.argv[1]

PROJECTION_YEARS = [2021, 2022, 2023, 2024, 2025, 2026]

files = glob.glob(path + "data/worldpopstats_*.csv")
dfs = []
for file in files:
    df = pd.read_csv(file)
    df["year"] = int(file.split("_")[-1][:-4])
    if projected_variable not in df.columns:
        print(f"skip {os.path.basename(file)}: no '{projected_variable}' column")
        continue
    n_nan = df[projected_variable].isna().sum()
    print(f"{os.path.basename(file)}: {len(df)} rows, {n_nan} NaN in {projected_variable}")
    dfs.append(df[["object_id", "year", projected_variable]])

master_df = pd.concat(dfs).sort_values(by="year").reset_index(drop=True)


def extrapolate_variable(rc_data):
    rc_data = rc_data.dropna(subset=[projected_variable])
    if len(rc_data) < 2:                      # can't fit a line
        return [np.nan] * len(PROJECTION_YEARS)

    model = LinearRegression()
    model.fit(rc_data[["year"]].values, rc_data[projected_variable].values)
    return model.predict(np.array(PROJECTION_YEARS).reshape(-1, 1)).tolist()


extrapolated = master_df.groupby("object_id")[["year", projected_variable]].apply(extrapolate_variable)

extrapolated_df = pd.DataFrame(
    extrapolated.tolist(), columns=[str(y) for y in PROJECTION_YEARS], index=extrapolated.index
).reset_index()

extrapolated_df = pd.melt(
    extrapolated_df, id_vars=["object_id"], var_name="year", value_name=projected_variable
)

out = path + "data/" + projected_variable + "_projections.csv"
extrapolated_df.to_csv(out, index=False)
print(f"Saved {out}  shape={extrapolated_df.shape}  NaN={extrapolated_df[projected_variable].isna().sum()}")