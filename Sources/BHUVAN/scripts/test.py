import rasterio
import numpy as np
import glob

path = "/Users/stephensmathew/cdl_rep/flood-data-ecosystem-Assam/Sources/BHUVAN"
files = glob.glob(path + "/data/tiffs/*.tif")

with rasterio.open(files[0]) as r:
    arr = r.read()
    print("Shape:", arr.shape)
    print("\nBand 4 (Alpha) unique values:", np.unique(arr[3]))
    print("Band 4 max:", arr[3].max())
    print("Band 4 nonzero count:", np.count_nonzero(arr[3]))
    print("\nBand 1 unique values:", np.unique(arr[0])[:20])
    print("Band 1 nonzero count:", np.count_nonzero(arr[0]))