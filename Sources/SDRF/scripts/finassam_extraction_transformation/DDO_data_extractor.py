#import camelot
import camelot
import pandas as pd
# Path to the PDF file
pdf_path = r"D:\CivicDataLab_IDS-DRR\IDS-DRR_Github\IDS-DRR-Assam\Sources\SDRF\data\ddo treasurycode DEPTNAME.pdf"

tables = camelot.read_pdf(pdf_path, pages="all", flavor="lattice")

# try using the 'stream' flavor instead.
if not tables:
    tables = camelot.read_pdf(pdf_path, pages="all", flavor="stream")

# Combine all extracted tables (if more than one) into a single DataFrame.
df = pd.concat([table.df for table in tables], ignore_index=True)

# Export the DataFrame to a CSV file.

if len(tables) > 1:
    combined_df = pd.concat([table.df for table in tables], ignore_index=True)
    combined_df.to_csv(r"D:\CivicDataLab_IDS-DRR\IDS-DRR_Github\IDS-DRR-Assam\Sources\SDRF\data\research\ddo_treasurycode_deptname.csv", index=False)
else:
    tables[0].to_csv(r"D:\CivicDataLab_IDS-DRR\IDS-DRR_Github\IDS-DRR-Assam\Sources\SDRF\data\research\ddo_treasurycode_deptname.csv", index=False)

print("CSV extraction complete, output saved to 'output.csv'")
