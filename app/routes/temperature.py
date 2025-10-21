from fastapi import APIRouter, HTTPException, Query
from typing import List
import httpx
from datetime import datetime
from app.models import TemperatureSummary, TemperatureByYear, ErrorResponse

router = APIRouter(prefix="/api/v1", tags=["Temperature"])


@router.get("/temperature-summary", response_model=TemperatureSummary)
async def get_temperature_summary(
    lat: float = Query(..., ge=-90, le=90, description="Latitude coordinate"),
    lng: float = Query(..., ge=-180, le=180, description="Longitude coordinate")
):
    """
    Returns current temperature, earliest recorded temperature, and temperature
    difference from historical average for the specified coordinates.
    """
    try:
        # Get historical data from 1940 to last year
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
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        
        # Process the data to calculate yearly averages
        daily_data = data.get("daily", {})
        times = daily_data.get("time", [])
        temperatures = daily_data.get("temperature_2m_mean", [])
        
        if not times or not temperatures:
            raise HTTPException(
                status_code=500,
                detail={"message": "No temperature data available for this location", "code": "NO_DATA"}
            )
        
        # Group by year and calculate averages
        yearly_temps = {}
        for time_str, temp in zip(times, temperatures):
            if temp is None:
                continue
            year = int(time_str.split("-")[0])
            if year not in yearly_temps:
                yearly_temps[year] = []
            yearly_temps[year].append(temp)
        
        # Calculate average for each year
        yearly_averages = {
            year: sum(temps) / len(temps)
            for year, temps in yearly_temps.items()
            if temps
        }
        
        if not yearly_averages:
            raise HTTPException(
                status_code=500,
                detail={"message": "Could not calculate temperature averages", "code": "CALCULATION_ERROR"}
            )
        
        # Get earliest and current (latest) year temperatures
        sorted_years = sorted(yearly_averages.keys())
        earliest_year = sorted_years[0]
        latest_year = sorted_years[-1]
        
        earliest_temp = yearly_averages[earliest_year]
        current_temp = yearly_averages[latest_year]
        temp_difference = current_temp - earliest_temp
        
        return TemperatureSummary(
            current_temperature=round(current_temp, 2),
            earliest_temperature=round(earliest_temp, 2),
            temperature_difference=round(temp_difference, 2),
            updated_at=datetime.utcnow()
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


@router.get("/temperature-graph", response_model=List[TemperatureByYear])
async def get_temperature_graph(
    lat: float = Query(..., ge=-90, le=90, description="Latitude coordinate"),
    lng: float = Query(..., ge=-180, le=180, description="Longitude coordinate")
):
    """
    Returns an array of average mean temperatures for each year in the
    historical record for the specified coordinates.
    """
    try:
        # Get historical data from 1940 to last year
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
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        
        # Process the data to calculate yearly averages
        daily_data = data.get("daily", {})
        times = daily_data.get("time", [])
        temperatures = daily_data.get("temperature_2m_mean", [])
        
        if not times or not temperatures:
            raise HTTPException(
                status_code=500,
                detail={"message": "No temperature data available for this location", "code": "NO_DATA"}
            )
        
        # Group by year and calculate averages
        yearly_temps = {}
        for time_str, temp in zip(times, temperatures):
            if temp is None:
                continue
            year = int(time_str.split("-")[0])
            if year not in yearly_temps:
                yearly_temps[year] = []
            yearly_temps[year].append(temp)
        
        # Calculate average for each year and create response
        result = []
        for year in sorted(yearly_temps.keys()):
            temps = yearly_temps[year]
            if temps:
                avg_temp = sum(temps) / len(temps)
                result.append(TemperatureByYear(
                    year=year,
                    avg_mean_temperature=round(avg_temp, 2)
                ))
        
        if not result:
            raise HTTPException(
                status_code=500,
                detail={"message": "Could not calculate temperature averages", "code": "CALCULATION_ERROR"}
            )
        
        return result
        
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

