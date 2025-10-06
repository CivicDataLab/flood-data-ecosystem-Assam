import os
import subprocess
import timeit
from osgeo import gdal

gdal.DontUseExceptions()

path = os.getcwd() + "/Sources/BHUVAN/"
os.makedirs(path + "data/tiffs/", exist_ok=True)

date_strings = [
    # 2025 August–September
    "2025_21_09_18",
    "2025_20_09_10",
    "2025_19_09_10",
    "2025_19_09_06",
    "2025_16_09_18",
    "2025_13_08_18",
    "2025_09_08_06"  
]

layer_code = "as"  # for assam 
layer = f"flood%3A{layer_code}"
bbox_as = "89.6922970,23.990548,96.0205936,28.1690311"
url_as = "https://bhuvan-gp1.nrsc.gov.in/bhuvan/wms"

for dates in date_strings:
    input_xml_path = path + f"/data/inundation_{dates}.xml"
    output_tiff_path = path + f"/data/tiffs/{dates}.tif"

    # Download WMS layer as XML
    command = [
        "gdal_translate",
        "-of", "WMS",
        f"WMS:{url_as}?&LAYERS={layer}_{dates}&TRANSPARENT=TRUE&SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&STYLES=&FORMAT=image%2Fpng&SRS=EPSG%3A4326&BBOX={bbox_as}",
        input_xml_path,
    ]
    subprocess.run(command, check=True)

    # Warp to GeoTIFF
    print(f"\nWarping {dates} started...")
    starttime = timeit.default_timer()

    gdal.Warp(
        output_tiff_path,
        input_xml_path,
        format="GTiff",
        xRes=0.00044915,
        yRes=-0.00044915,
        creationOptions=["COMPRESS=DEFLATE", "TILED=YES"],
        callback=gdal.TermProgress,
    )

    print("Time took to Warp: ", round(timeit.default_timer() - starttime, 2), "seconds")
    print(f"✅ Warping completed. Output saved to: {output_tiff_path}")
    

  #2025 June–July
    #"2025_13_07_18",
    #"2025_11_07_10",
    #"2025_08_07_06",
    #"2025_06_07_18",
    #"2025_05_07_18",
    #"2025_07_04_10",
    #"2025_03_07_10",
    #"2025_03_06_10",
    #"2025_28_06_11",
    #"2025_27_06_18",
    #"2025_26_06_06",
    #"2025_24_06_18",
    #"2025_19_06_18",
    #"2025_31_05_12_06",  
    #"2025_17_06_18",
    #"2025_17_06_10",
    #"2025_12_06_18",
    #"2025_12_06_10",
    #"2025_11_06_10",
    #"2025_10_06_11",
    #"2025_09_06_18",
    #"2025_09_06_06",
    #"2025_09_06_10",
    #"2025_08_06_06",
    #"2025_07_06_18",
    #"2025_06_06_06",
    #"2025_04_06_18",
    #"2025_03_06_06",
    #"2025_01_06_06",
    # Uncomment 2024 if needed
    # "2024_04_07_18",
    # "2024_03_07_06",
    # "2024_01_07_18",