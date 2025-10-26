from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Tuple, Optional
import httpx
from datetime import datetime, timedelta
from app.models import TemperatureSummary, TemperatureByYear, TemperatureData, TemperatureTrend, ErrorResponse
import asyncio
import math
from functools import lru_cache
from collections import OrderedDict, defaultdict

router = APIRouter(prefix="/api/v1", tags=["Temperature"])

# LRU Cache for storing API responses with bounded memory
class LRUCache:
    def __init__(self, max_size: int = 100, ttl: timedelta = timedelta(minutes=5)):
        self.max_size = max_size
        self.ttl = ttl
        self._cache = OrderedDict()
    
    def get(self, key: str) -> Optional[Tuple[Dict[str, Any], datetime]]:
        if key not in self._cache:
            return None
        
        data, timestamp = self._cache[key]
        if datetime.now() - timestamp > self.ttl:
            del self._cache[key]
            return None
        
        # Move to end (most recently used)
        self._cache.move_to_end(key)
        return (data, timestamp)
    
    def set(self, key: str, value: Dict[str, Any], timestamp: datetime = None):
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

_cache = LRUCache(max_size=200, ttl=timedelta(minutes=5))

# Persistent HTTP client with connection pooling for better performance
_http_client: Optional[httpx.AsyncClient] = None


def get_http_client() -> httpx.AsyncClient:
    """Get or create persistent HTTP client with optimized settings."""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(15.0, connect=5.0),
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
        )
    return _http_client


async def close_http_client():
    """Close the persistent HTTP client."""
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None


async def get_temperature_data_with_retry(url: str, params: dict, max_retries: int = 3) -> Dict[str, Any]:
    """
    Fetch data from API with exponential backoff retry logic.
    Uses persistent HTTP client for better connection pooling.
    """
    last_exception = None
    client = get_http_client()
    
    for attempt in range(max_retries):
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            last_exception = e
            if attempt < max_retries - 1:
                # Exponential backoff: 1s, 2s, 4s
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)
            else:
                raise
    
    raise last_exception


async def get_temperature_data_cached(lat: float, lng: float) -> Dict[str, Any]:
    """
    Fetch temperature data from Open-Meteo API with caching and retry logic.
    Returns cached data if available and not expired, otherwise fetches fresh data.
    """
    # Create cache key based on coordinates (rounded to reasonable precision)
    cache_key = f"{round(lat, 4)}_{round(lng, 4)}"
    
    # Check if we have valid cached data
    cached_result = _cache.get(cache_key)
    if cached_result is not None:
        cached_data, _ = cached_result
        return cached_data
    
    # Fetch fresh data from API
    current_year = datetime.now().year
    last_year = current_year - 1
    start_date = "1940-01-01"
    end_date = f"{last_year}-12-31"
    
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lng,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "temperature_2m_mean"
    }
    
    data = await get_temperature_data_with_retry(url, params)
    
    # Store in cache
    _cache.set(cache_key, data)
    
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
async def get_temperature_data(
    lat: float = Query(..., ge=-90, le=90, description="Latitude coordinate"),
    lng: float = Query(..., ge=-180, le=180, description="Longitude coordinate")
):
    """
    Returns combined temperature data including summary (current, earliest, difference) 
    and yearly breakdown for the specified coordinates.
    """
    try:
        # Get historical data using cached function
        data = await get_temperature_data_cached(lat, lng)
        
        # Process the data to calculate yearly averages
        daily_data = data.get("daily", {})
        times = daily_data.get("time", [])
        temperatures = daily_data.get("temperature_2m_mean", [])
        
        if not times or not temperatures:
            raise HTTPException(
                status_code=500,
                detail={"message": "No temperature data available for this location", "code": "NO_DATA"}
            )
        
        # Group by year and calculate averages using defaultdict for efficiency
        yearly_temps = defaultdict(lambda: [0.0, 0])  # [sum, count] for each year
        
        for time_str, temp in zip(times, temperatures):
            if temp is None:
                continue
            year = int(time_str[:4])  # Extract year directly without split for speed
            yearly_temps[year][0] += temp
            yearly_temps[year][1] += 1
        
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
        
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=503,
            detail={"message": f"External API error: {str(e)}", "code": "EXTERNAL_API_ERROR"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"message": f"Internal server error: {str(e)}", "code": "INTERNAL_ERROR"}
        )