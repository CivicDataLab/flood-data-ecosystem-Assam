# ### SEC-SDRF procurements   

import pandas as pd
import os
import glob
import re
from dateutil import parser
import matplotlib

import geopandas as gpd
from fuzzywuzzy import fuzz
from fuzzywuzzy import process


sdrf = pd.read_csv(r'Sources/TENDERS/data/SDRF/SEC/45th to 50th SEC - Summary.csv')
sdrf_51_54 = pd.read_csv(r'Sources/TENDERS/data/SDRF/SEC/extracted/51_to_54th_SEC_flood_related_allocations_aggregated.csv')
rc_gdf = gpd.read_file(r'Maps/Geojson/assam_rc_2024-11.geojson')

output_dir = r'Sources/TENDERS/data/variables/SDRF_sanctions_awarded_value'


sdrf = sdrf.rename(columns={'District ':'District'})
sdrf['District'] = sdrf['District'].str.title()

melted_df = sdrf.melt(id_vars=['District'], 
                    value_vars=['46 SDRF TENDER (lakhs)', '47 SDRF TENDER (lakhs) ', 
                                '48 SDRF TENDER (lakhs) ', '49 SDRF TENDER (lakhs) ', 
                                '50 SDRF TENDER (lakhs) '], 
                    var_name='SDRF Column', value_name='SDRF funding')

# Filter out rows where SDRF funding is 0
melted_df = melted_df[melted_df['SDRF funding'] > 0]

# Create a mapping of SDRF columns to timeperiods
timeperiod_map = {
    '46 SDRF TENDER (lakhs)': '2022_03',
    '47 SDRF TENDER (lakhs) ': '2023_02',
    '48 SDRF TENDER (lakhs) ': '2023_03',
    '49 SDRF TENDER (lakhs) ': '2023_09',
    '50 SDRF TENDER (lakhs) ': '2024_03'
}

# Map the SDRF columns to the corresponding timeperiod
melted_df['timeperiod'] = melted_df['SDRF Column'].map(timeperiod_map)
# Drop the SDRF Column as it's no longer needed
melted_df = melted_df.drop(columns=['SDRF Column'])
# Reorder the columns for better readability
melted_df = melted_df[['District','timeperiod', 'SDRF funding']]
melted_df['SDRF funding'] = melted_df['SDRF funding']*100000

# Standardize district names to title case before concatenating
melted_df['District'] = melted_df['District'].str.lower()
sdrf_51_53['District'] = sdrf_51_53['District'].str.lower()

melted_df = pd.concat([melted_df, sdrf_51_53], ignore_index=True)

def fuzzy_merge(df_1, df_2, key1, key2, threshold=90, limit=2):
    """
    :param df_1: the left table to join
    :param df_2: the right table to join
    :param key1: key column of the left table
    :param key2: key column of the right table
    :param threshold: how close the matches should be to return a match, based on Levenshtein distance
    :param limit: the amount of matches that will get returned, these are sorted high to low
    :return: dataframe with boths keys and matches
    """
    s = df_2[key2].tolist()

    m = df_1[key1].apply(lambda x: process.extract(x, s, limit=limit))    
    df_1['matches'] = m

    m2 = df_1['matches'].apply(lambda x: ', '.join([i[0] for i in x if i[1] >= threshold]))
    df_1['matches'] = m2

    return df_1


fuzzymatch = fuzzy_merge(rc_gdf, melted_df, 'dtname', 'District', threshold=80,limit=1)
# Step 1: Merge df1 with the revenue_circle_data
merged_df = pd.merge(melted_df,fuzzymatch, left_on='District', right_on='matches')

# Step 2: Calculate the number of revenue circles for each district
revenue_circle_count = fuzzymatch.groupby('matches')['revenue_ci'].count().reset_index()
revenue_circle_count.columns = ['matches', 'num_revenue_circles']

# Step 3: Merge the revenue circle count into the merged dataframe
merged_df = merged_df.merge(revenue_circle_count, on='matches')

# Step 4: Divide the columns 'SDRF_RC' by the number of revenue circles
merged_df['SDRF_RC'] = merged_df['SDRF funding'] / merged_df['num_revenue_circles']

# Step 5: Drop the unnecessary columns if needed
interpolated = merged_df.drop(columns=['dtname', 'num_revenue_circles','geometry','HQ','revenue_cr'])
interpolated['District'] = interpolated['District'].str.upper()
interpolated = interpolated.rename(columns={'District':'DISTRICT'})
interpolated.to_csv(r'Sources/TENDERS/data/SDRF/SEC/SEC_SDRF.csv')
sdrf_new = interpolated.copy()
print(sdrf_new.columns)
# Step 1: Ensure the output directory exists
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Step 2: Group the data by timeperiod
for timeperiod in sdrf_new['timeperiod'].unique():
    # Step 3: Filter the DataFrame for the specific timeperiod and extract the relevant columns
    filtered_df = sdrf_new[sdrf_new['timeperiod'] == timeperiod][['object_id', 'SDRF_RC']]
    
    # Step 4: Rename the 'SDRF_RC' column to 'SDRF_sanctions_awarded_value'
    filtered_df = filtered_df.rename(columns={'SDRF_RC': 'SDRF_sanctions_awarded_value'})
    
    # Step 5: Construct the file name and path
    filename = f"SDRF_sanctions_awarded_value_{timeperiod}.csv"
    file_path = os.path.join(output_dir, filename)
    
    # Step 6: Save the DataFrame to CSV
    filtered_df.to_csv(file_path, index=False)


