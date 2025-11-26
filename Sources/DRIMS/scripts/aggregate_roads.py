import pandas as pd

# Read the three CSV files
df_05 = pd.read_csv('data/variables/Roads/Roads_2025_05.csv')
df_06 = pd.read_csv('data/variables/Roads/Roads_2025_06.csv')
df_07 = pd.read_csv('data/variables/Roads/Roads_2025_07.csv')

# Concatenate all three dataframes
combined_df = pd.concat([df_05, df_06, df_07], ignore_index=True)

# Group by object_id and sum the Roads column
aggregated_df = combined_df.groupby('object_id')['Roads'].sum().reset_index()

# Sort by object_id for better readability
aggregated_df = aggregated_df.sort_values('object_id').reset_index(drop=True)

# Save to a new CSV file
aggregated_df.to_csv('data/variables/Roads/Roads_2025_05_06_07_aggregated.csv', index=False)

print(f"Aggregated file created successfully!")
print(f"Total unique object_ids: {len(aggregated_df)}")
print(f"\nFirst 10 rows:")
print(aggregated_df.head(10))
