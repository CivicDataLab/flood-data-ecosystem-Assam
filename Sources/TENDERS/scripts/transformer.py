import pandas as pd
import os
import geopandas as gpd

data_path = os.getcwd()+r'/Sources/TENDERS/data/'
assam_rc_gdf = gpd.read_file(os.getcwd()+r'/Maps/Geojson/assam_rc_2024-11.geojson')

flood_tenders_geotagged_df = pd.read_csv(data_path + r'floodtenders_RCgeotagged.csv')
flood_tenders_geotagged_df = flood_tenders_geotagged_df.merge(assam_rc_gdf,
                                 left_on = ['DISTRICT_FINALISED', 'REVENUE_CIRCLE_FINALISED'],
                                 right_on = ['dtname', 'revenue_ci'],
                                 how='left')

flood_tenders_geotagged_df['Awarded Value'] = flood_tenders_geotagged_df['Awarded Value'].str.replace(',', '').astype(float)

# Total tender variable
variable = 'total_tender_awarded_value'
total_tender_awarded_value_df = flood_tenders_geotagged_df.groupby(['month', 'object_id'])[['Awarded Value']].sum().reset_index()
total_tender_awarded_value_df = total_tender_awarded_value_df.rename(columns = {'Awarded Value': variable})

for year_month in total_tender_awarded_value_df.month.unique():
    variable_df_monthly = total_tender_awarded_value_df[total_tender_awarded_value_df.month == year_month]
    variable_df_monthly = variable_df_monthly[['object_id', variable]]
    print(data_path)
    if os.path.exists(data_path+'variables/'+variable):
        variable_df_monthly.to_csv(data_path+'variables/'+variable+'/{}_{}.csv'.format(variable, year_month), index=False)
    else:
        os.mkdir(data_path+'variables/'+variable)
        variable_df_monthly.to_csv(data_path+'variables/'+variable+'/{}_{}.csv'.format(variable, year_month), index=False)

# Scheme wise tender variables
variables = flood_tenders_geotagged_df['Scheme'].unique()
for variable in variables:
    variable_df = flood_tenders_geotagged_df[flood_tenders_geotagged_df['Scheme'] == variable]
    variable_df= variable_df.groupby(['month', 'object_id'])[['Awarded Value']].sum().reset_index()
    
    variable = str(variable) + '_tenders_awarded_value'
    variable_df = variable_df.rename(columns = {'Awarded Value': variable})
    
    for year_month in variable_df.month.unique():
        variable_df_monthly = variable_df[variable_df.month == year_month]
        variable_df_monthly = variable_df_monthly[['object_id', variable]]
        if os.path.exists(data_path+'variables/'+variable):
            variable_df_monthly.to_csv(data_path+'variables/'+variable+'/{}_{}.csv'.format(variable, year_month), index=False)
        else:
            os.mkdir(data_path+'variables/'+variable)
            variable_df_monthly.to_csv(data_path+'variables/'+variable+'/{}_{}.csv'.format(variable, year_month), index=False)


# Scheme wise tender variables
variables = flood_tenders_geotagged_df['Response Type'].unique()
for variable in variables:
    variable_df = flood_tenders_geotagged_df[flood_tenders_geotagged_df['Response Type'] == variable]
    variable_df= variable_df.groupby(['month', 'object_id'])[['Awarded Value']].sum().reset_index()

    variable = str(variable) + '_tenders_awarded_value'
    variable_df = variable_df.rename(columns = {'Awarded Value': variable})
    
    for year_month in variable_df.month.unique():
        variable_df_monthly = variable_df[variable_df.month == year_month]
        variable_df_monthly = variable_df_monthly[['object_id', variable]]
        if os.path.exists(data_path+'variables/'+variable):
            variable_df_monthly.to_csv(data_path+'variables/'+variable+'/{}_{}.csv'.format(variable, year_month), index=False)
        else:
            os.mkdir(data_path+'variables/'+variable)
            variable_df_monthly.to_csv(data_path+'variables/'+variable+'/{}_{}.csv'.format(variable, year_month), index=False)