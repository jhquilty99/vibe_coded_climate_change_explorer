import xarray as xr
import pandas as pd
from pathlib import Path

# Get the absolute path to the zarr store
_base_path = Path(__file__).parent.parent.parent
zarr_store_path = _base_path / 'external_data' / 'era5_temperature_1940_2024.zarr'

# Global variable to hold the opened dataset (lazy loading)
_ds = None

def get_dataset():
    """Get or open the Zarr dataset (lazy initialization)."""
    global _ds
    if _ds is None:
        _ds = xr.open_zarr(str(zarr_store_path), consolidated=True)
    return _ds

def query_era5(latitude: float, longitude: float) -> pd.Series:
    """
    Query the ERA5 temperature data for a specific point in space (latitude/longitude).
    
    Args:
        latitude: Latitude coordinate in degrees north (must be between -90 and 90)
        longitude: Longitude coordinate in degrees east (will be converted from -180/180 to 0/360 range)
        
    Returns:
        pandas Series with temperature data indexed by time, in degrees Celsius
        (temperature is converted from Kelvin to Celsius)
    """
    # Convert longitude from -180/180 range to 0/360 range if needed
    longitude = 360 + longitude 
    if longitude > 360:
        longitude = longitude - 360
    
    ds = get_dataset()
    data_array = ds['t2m'].sel(latitude=latitude, longitude=longitude, method='nearest').load()
    
    # Get the actual coordinates that were selected (nearest point)
    selected_lat = data_array.latitude.values
    selected_lon = data_array.longitude.values
    print(f"Requested: ({latitude}, {longitude}), Selected: ({selected_lat}, {selected_lon})")
    
    # Convert from Kelvin to Celsius
    data_array = data_array - 273.15
    
    # Drop scalar coordinates that cause "Too many indexers" error when converting to pandas
    # These are dimensions with shape [] (empty shape) like number, step, surface
    scalar_coords = [name for name, coord in data_array.coords.items() if coord.shape == ()]
    if scalar_coords:
        data_array = data_array.drop_vars(scalar_coords)
    
    return data_array.to_pandas().squeeze()

if __name__ == "__main__":
    df = query_era5(40.7128, -74.0060).head(12)
    print(df)