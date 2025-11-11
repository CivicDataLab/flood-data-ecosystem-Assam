import glob
import os
import subprocess

cwd = os.getcwd()
path = os.path.join(cwd, "Sources/BHUVAN/")
script_path = os.path.join(cwd, "Sources/BHUVAN/scripts/transformer.py")
PY = "/Users/stephensmathew/anaconda3/envs/flood_env/bin/python"

print(path)
for year in [2025]:
    print(year)
    year = str(year)
    for month in ["06","07","08","09"]:
        files1 = glob.glob(path + f"data/tiffs/removed_watermarks/{year}_??_{month}*.tif")
        files2 = glob.glob(path + f"data/tiffs/removed_watermarks/{year}_??-??_{month}*.tif")
        files = files1 + files2
        if not files:
            print(f"No files for the month {month}")
            continue

        print("Number of images:", len(files))
        subprocess.run([PY, script_path, year, month],
            check=True
        )
