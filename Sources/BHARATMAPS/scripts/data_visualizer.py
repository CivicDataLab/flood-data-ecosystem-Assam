import os
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt

# Define the root folder and variables
root_folder = r'D:\CivicDataLab_IDS-DRR\IDS-DRR_Github\Deployment\flood-data-ecosystem-Assam\Sources\BHARATMAPS\data\variables'
variables = ["health_centres_count", "rail_length", "road_length", "schools_count"]
variable_folder = ["HealthCenters", "RailLengths", "RoadLengths", "Schools"]
shp_path = r'D:\CivicDataLab_IDS-DRR\IDS-DRR_Github\Deployment\flood-data-ecosystem-Assam\Maps\Geojson\assam_rc_2024-11.geojson'

# Load shapefile
shp = gpd.read_file(shp_path)

# Initialize an empty DataFrame to store the merged data
merged_df = pd.DataFrame()

# Loop through each variable folder
for variable, folder in zip(variables, variable_folder):
    variable_folder_path = os.path.join(root_folder, folder)  # Correct folder path

    # Check if the folder exists
    if not os.path.exists(variable_folder_path):
        print(f"Skipping {variable}: Folder '{folder}' not found.")
        continue

    # Loop through each CSV file in the variable folder
    for csv_file in os.listdir(variable_folder_path):
        if csv_file.endswith('.csv'):
            try:
                # Read the CSV file
                file_path = os.path.join(variable_folder_path, csv_file)
                df = pd.read_csv(file_path)

                # Ensure 'object_id' column exists
                if 'object_id' not in df.columns:
                    print(f"Skipping {csv_file}: 'object_id' column is missing.")
                    continue

                # Rename the variable column to 'value'
                if variable not in df.columns:
                    print(f"Skipping {csv_file}: Expected column '{variable}' not found.")
                    continue
                
                df.rename(columns={variable: 'value'}, inplace=True)

                # Add variable name for tracking
                df['variable'] = variable

                # Append the DataFrame to merged_df
                merged_df = pd.concat([merged_df, df], ignore_index=True)

            except Exception as e:
                print(f"Error processing {csv_file}: {e}")


# Pivot the DataFrame
pivot_df = merged_df.pivot_table(index=['object_id'], columns='variable', values='value').reset_index()

# Merge with shapefile
shp_merge = pivot_df.merge(shp[['object_id', 'dtname', 'revenue_ci','geometry']], on='object_id', how='left')

# Create output folder for visualizations
output_folder = r'D:\CivicDataLab_IDS-DRR\IDS-DRR_Github\Deployment\flood-data-ecosystem-Assam\Sources\BHARATMAPS\visualizations'
os.makedirs(output_folder, exist_ok=True)

shp_merge = gpd.GeoDataFrame(shp_merge, geometry='geometry')



# Generate and save visualizations
for variable in variables:
    # Choropleth map
    #year = 2024  # Adjust based on available years
    #shp_year = shp_merge[shp_merge['year'] == year]

    fig, ax = plt.subplots(figsize=(10, 5))
    shp_merge.plot(column=variable,  
                cmap='RdYlBu_r',  # choose a color map, e.g., OrRd for shades of red
                linewidth=0.8,
                ax=ax,
                #edgecolor='0.8',
                legend=True,
                legend_kwds={
                  'shrink': 0.5,  # Adjusts the size of the color bar (default is 1)
                  'aspect': 30,    # Controls the aspect ratio of the color bar
                  'label': variable,  # Label for the color bar
                }
                  )
    ax.tick_params(labelsize=8)
    plt.title(f'{variable} in Assam')
    output_path = os.path.join(output_folder, f'{variable}_map.png')
    plt.savefig(output_path, dpi=300)
    plt.close()

    ## Line chart over years
    #fig, ax = plt.subplots()
    #kok = shp_merge[shp_merge['dtname'] == 'KOKRAJHAR']
    #kok_grouped = kok.groupby(['year'])[variable].mean().reset_index()

    # Plot using 'year' as the x-axis
    #ax.plot(kok[variable], marker='o', linestyle='-')    
    #plt.title(f'{variable} in Kokrajhar over the years')
    #plt.xlabel('year')
    #plt.ylabel(variable)
    #output_path = os.path.join(output_folder, f'{variable}_line_chart.png')
    #plt.savefig(output_path, dpi=300)
    #plt.close()

# Display the first few rows of the merged DataFrame
print(shp_merge.head())
shp_reduced = shp_merge.drop(columns=['geometry'])
# Save merged DataFrame to CSV
output_file = os.path.join(root_folder, 'BharatMaps_variables.csv')
shp_merge.to_csv(output_file, index=False)
print(f'Merged CSV file saved to {output_file}')
