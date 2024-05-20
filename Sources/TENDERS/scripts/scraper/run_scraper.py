import os
import subprocess
from datetime import date, timedelta

cwd = os.getcwd()
script_path = (
    cwd
    + "/Sources/TENDERS/scripts/scraper/scraper_assam_recent_tenders_tender_status.py"
)

for year in range(2023, 2024):
    year = str(year)
    for month in range(1, 5):
        month = str(month)
        print(year + "_" + month)
        subprocess.call(["python3", script_path, year, month])
