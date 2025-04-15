import ee
import geemap
import os 
import time
import rasterio
import geopandas as gpd
import rasterstats
import pandas as pd

service_account = ' idsdrr@ee-idsdrr.iam.gserviceaccount.com'
credentials = ee.ServiceAccountCredentials(service_account, r'Sources/NASADEM/ee-idsdrr-d856f70748a7.json')
ee.Initialize(credentials)

cwd = os.getcwd()
assam_rc_gdf = gpd.read_file(cwd+r'\Maps\Geojson\assam_rc_2024-11.geojson')



assam_rcs = ee.FeatureCollection("projects/ee-idsdrr/assets/assam_rc_180")
geometry = assam_rcs.geometry() 

# Get GEE Image
nasadem = ee.Image('NASA/NASADEM_HGT/001')
elevation = nasadem.select('elevation')
task = ee.batch.Export.image.toDrive(image=elevation.clip(geometry),
                                     region=geometry,
                                     description='NASADEM_DEM_30',
                                     folder='NASADEM',
                                     scale= 30,
                                     maxPixels=1e13)
task.start()
print('Task ID:', task.id)

slope = ee.Terrain.slope(elevation)
task = ee.batch.Export.image.toDrive(image=slope.clip(geometry),
                                     region=geometry,
                                     description='NASADEM_SLOPE_30',
                                     folder='NASADEM',
                                     scale= 30,
                                     maxPixels=1e13)
task.start()
print('Task ID:', task.id)
