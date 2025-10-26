import xarray as xr

# Define the path to your large GRIB file and the output Zarr store
grib_file_path = 'era5_temperature_1940_2024.grib'
zarr_store_path = 'era5_temperature_1940_2024.zarr'

# Open the GRIB dataset using xarray with the cfgrib engine
# The 'chunks' argument is crucial for performance.
# This tells Dask to process the file in manageable pieces.
# We use 'auto' here, but you can specify manual chunks like {'time': 10}.
ds = xr.open_dataset(
    grib_file_path,
    engine='cfgrib',
    chunks='auto' 
)

print("Dataset opened successfully. Here are the dimensions:")
print(ds.dims)

# Save the dataset to Zarr format. This might take some time for a large file.
# The 'consolidated=True' flag creates a metadata file for faster reads.
print(f"Saving to Zarr store at: {zarr_store_path}")
ds.to_zarr(zarr_store_path, consolidated=True, mode='w')

print("Conversion to Zarr complete! ✨")