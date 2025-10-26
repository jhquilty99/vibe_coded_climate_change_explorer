import xarray as xr
import pandas as pd

zarr_store_path = '../external_data/era5_temperature_1940_2024.zarr'

# Open the Zarr store. This operation is extremely fast as it only reads metadata.
ds = xr.open_zarr(zarr_store_path, consolidated=True)

print("Zarr store opened. Dataset variables:")
print(ds.data_vars)

def query_era5(latitude: float, longitude: float) -> pd.DataFrame:
    """
    Query the ERA5 temperature data for a specific point in space (latitude/longitude)
    """
    data_array = ds['t2m'].sel(latitude=latitude, longitude=longitude, method='nearest').load()
    return data_array.to_pandas()