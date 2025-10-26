from fastapi import APIRouter, HTTPException, Query
from typing import Any, Tuple, Optional, List
from datetime import datetime, timedelta
from app.models import TemperatureSummary, TemperatureByYear, TemperatureData, TemperatureTrend
from external_data.utils.query_era5 import query_era5
from collections import OrderedDict, defaultdict
import pandas as pd

router = APIRouter(prefix="/api/v1", tags=["Temperature"])

# LRU Cache for storing API responses with bounded memory
class LRUCache:
    def __init__(self, max_size: int = 100, ttl: timedelta = timedelta(minutes=60)):
        self.max_size = max_size
        self.ttl = ttl
        self._cache = OrderedDict()
    
    def get(self, key: str) -> Optional[Tuple[Any, datetime]]:
        if key not in self._cache:
            return None
        
        data, timestamp = self._cache[key]
        if datetime.now() - timestamp > self.ttl:
            del self._cache[key]
            return None
        
        # Move to end (most recently used)
        self._cache.move_to_end(key)
        return (data, timestamp)
    
    def set(self, key: str, value: Any, timestamp: datetime = None):
        if timestamp is None:
            timestamp = datetime.now()
        
        if key in self._cache:
            self._cache.move_to_end(key)
        
        self._cache[key] = (value, timestamp)
        
        # Evict oldest if over max size
        if len(self._cache) > self.max_size:
            self._cache.popitem(last=False)
    
    def clear(self):
        self._cache.clear()

_cache = LRUCache(max_size=200, ttl=timedelta(minutes=60))


def get_temperature_data_cached(lat: float, lng: float) -> pd.DataFrame:
    """
    Fetch temperature data from local ERA5 Zarr store with caching.
    Returns cached data if available and not expired, otherwise fetches fresh data.
    
    Returns:
        pandas DataFrame with temperature data indexed by time (converted from Series if needed)
    """
    # Create cache key based on coordinates (rounded to reasonable precision)
    cache_key = f"{round(lat, 4)}_{round(lng, 4)}"
    
    # Check if we have valid cached data
    cached_result = _cache.get(cache_key)
    if cached_result is not None:
        cached_data, _ = cached_result
        return cached_data.copy()  # Return a copy to avoid cache mutation
    
    # Fetch fresh data from local ERA5 Zarr store
    data = query_era5(lat, lng)
    
    # Convert Series to DataFrame if needed (for compatibility with downstream code)
    if isinstance(data, pd.Series):
        data = data.to_frame()
    
    # Store in cache (store a copy to avoid mutations)
    _cache.set(cache_key, data.copy())
    
    return data


def calculate_linear_regression(years: List[int], temperatures: List[float]) -> Tuple[float, float, float]:
    """
    Optimized single-pass linear regression calculation for temperature data over time.
    Uses online algorithms to reduce memory usage and improve performance.
    
    Args:
        years: List of years
        temperatures: List of corresponding temperatures
        
    Returns:
        Tuple of (slope, intercept, r_squared)
    """
    n = len(years)
    if n < 2:
        return 0.0, 0.0, 0.0
    
    # Single-pass calculation of necessary sums
    sum_x = 0.0
    sum_y = 0.0
    sum_xy = 0.0
    sum_x_sq = 0.0
    sum_y_sq = 0.0
    
    for year, temp in zip(years, temperatures):
        sum_x += year
        sum_y += temp
        sum_xy += year * temp
        sum_x_sq += year * year
        sum_y_sq += temp * temp
    
    # Calculate means
    x_mean = sum_x / n
    y_mean = sum_y / n
    
    # Calculate slope and intercept using pre-computed sums
    ss_xy = sum_xy - n * x_mean * y_mean
    ss_xx = sum_x_sq - n * x_mean * x_mean
    ss_yy = sum_y_sq - n * y_mean * y_mean
    
    if ss_xx == 0:
        return 0.0, y_mean, 0.0
    
    slope = ss_xy / ss_xx
    intercept = y_mean - slope * x_mean
    
    # Calculate R-squared using pre-computed sum
    if ss_yy == 0:
        r_squared = 1.0 if ss_xy == 0 else 0.0
    else:
        r_squared = (ss_xy ** 2) / (ss_xx * ss_yy)
    
    return slope, intercept, r_squared


@router.get("/temperature", response_model=TemperatureData)
def get_temperature_data(
    lat: float = Query(..., ge=-90, le=90, description="Latitude coordinate"),
    lng: float = Query(..., ge=-180, le=180, description="Longitude coordinate")
):
    """
    Returns combined temperature data including summary (current, earliest, difference) 
    and yearly breakdown for the specified coordinates.
    Uses local ERA5 data from Zarr store.
    """
    try:
        # Get historical data using cached function
        df = get_temperature_data_cached(lat, lng)
        
        # Check if data is available
        if df.empty:
            raise HTTPException(
                status_code=500,
                detail={"message": "No temperature data available for this location", "code": "NO_DATA"}
            )
        
        # Data is already in Celsius (converted in query_era5)
        # Ensure we have a DatetimeIndex
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
        
        # Extract temperature column (handle both Series and DataFrame)
        if isinstance(df, pd.Series):
            temperature_series = df
        else:
            temperature_series = df.iloc[:, 0]
        
        # For more accurate annual averages, weight each month by its number of days
        # This accounts for months having different lengths (28-31 days)
        # Create a dataframe with temperature and day weights
        df_processed = pd.DataFrame({
            'temperature_celsius': temperature_series.values,
            'days_in_month': df.index.to_period('M').to_timestamp(how='end').days_in_month
        }, index=df.index)
        df_processed['weighted_temp'] = df_processed['temperature_celsius'] * df_processed['days_in_month']
        
        # Group by year and calculate weighted averages
        yearly_temps = defaultdict(lambda: [0.0, 0])  # [sum_weighted_temp, sum_days]
        
        for timestamp, row in df_processed.iterrows():
            year = timestamp.year
            weighted_temp = row['weighted_temp']
            days = row['days_in_month']
            yearly_temps[year][0] += weighted_temp
            yearly_temps[year][1] += days
        
        # Calculate average for each year (more efficient)
        yearly_averages = {
            year: sum_count[0] / sum_count[1]
            for year, sum_count in yearly_temps.items()
            if sum_count[1] > 0
        }
        
        if not yearly_averages:
            raise HTTPException(
                status_code=500,
                detail={"message": "Could not calculate temperature averages", "code": "CALCULATION_ERROR"}
            )
        
        # Get earliest and current (latest) year temperatures for summary
        sorted_years = sorted(yearly_averages.keys())
        earliest_year = sorted_years[0]
        latest_year = sorted_years[-1]
        
        earliest_temp = yearly_averages[earliest_year]
        current_temp = yearly_averages[latest_year]
        temp_difference = current_temp - earliest_temp
        
        # Create summary
        summary = TemperatureSummary(
            current_temperature=round(current_temp, 2),
            earliest_temperature=round(earliest_temp, 2),
            temperature_difference=round(temp_difference, 2),
            updated_at=datetime.utcnow()
        )
        
        # Create yearly data array
        yearly_data = []
        years_list = []
        temperatures_list = []
        
        for year in sorted(yearly_averages.keys()):
            avg_temp = yearly_averages[year]
            yearly_data.append(TemperatureByYear(
                year=year,
                avg_mean_temperature=round(avg_temp, 2)
            ))
            years_list.append(year)
            temperatures_list.append(avg_temp)
        
        # Calculate linear regression trend
        slope, intercept, r_squared = calculate_linear_regression(years_list, temperatures_list)
        trend = TemperatureTrend(
            slope=round(slope, 6),  # More precision for slope since it's typically small
            intercept=round(intercept, 2),
            r_squared=round(r_squared, 4)
        )
        
        return TemperatureData(
            summary=summary,
            yearly_data=yearly_data,
            trend=trend
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"message": f"Internal server error: {str(e)}", "code": "INTERNAL_ERROR"}
        )