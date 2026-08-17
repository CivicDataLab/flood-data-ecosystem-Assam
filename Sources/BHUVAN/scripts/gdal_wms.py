import os
import subprocess
import timeit
from osgeo import gdal

gdal.DontUseExceptions()

path = os.getcwd() + "/Sources/BHUVAN/"
os.makedirs(path + "data/tiffs/", exist_ok=True)

date_strings = [
    "2026_30_07_06",
    "2026_29_07_06",
    "2026_27_07_18",
    "2026_26_07_10",
    "2026_26_07_18",
    "2026_23_07_18",
    "2026_21_07_06",
    "2026_22_07_18",
    "2026_20_07_18",
    "2026_18_07_18",
    "2026_17_07_18",
    "2026_16_07_18",
    "2026_15_07_18",
    "2026_14_07_18",
    "2026_10_07_18",
    "2026_05_07_06",
    "2026_13_07_18",
    "2026_13_07_06",
    "2026_10_07_06",
    "2026_09_07_18",
    "2026_08_07_18",
    "2026_05_07_18",
    "2026_06_07_06",
    "2026_28_06_18",
    "2026_26_06_06",
    "2026_22_06_18",
    "2026_21_06_18"
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
    

  