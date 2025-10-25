from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class TemperatureSummary(BaseModel):
    """Summary of current and historical temperature data for a location"""
    current_temperature: float = Field(..., description="Temperature by year for the latest year")
    earliest_temperature: float = Field(..., description="Temperature by year for the earliest year")
    temperature_difference: float = Field(..., description="Difference between current and earliest temperature in degrees Celsius")
    updated_at: datetime = Field(..., description="ISO 8601 timestamp of when the data was last updated")

    class Config:
        json_schema_extra = {
            "example": {
                "current_temperature": 22.5,
                "earliest_temperature": 18.3,
                "temperature_difference": 2.1,
                "updated_at": "2025-10-08T12:34:56.789Z"
            }
        }


class TemperatureByYear(BaseModel):
    """Average temperature data for a specific year"""
    avg_mean_temperature: float = Field(..., description="Average mean temperature for the year in degrees Celsius")
    year: int = Field(..., ge=1800, le=2100, description="Year of measurement")

    class Config:
        json_schema_extra = {
            "example": {
                "avg_mean_temperature": 21.8,
                "year": 2023
            }
        }


class GeocodingResponse(BaseModel):
    """Location information derived from coordinates"""
    admin_level_high: Optional[str] = Field(None, description="Admin level 10, 11, or 12 (city/town level)")
    admin_level_mid: Optional[str] = Field(None, description="Admin level 5, 6, 7, 8, or 9 (county/state/province level)")
    admin_level_low: Optional[str] = Field(None, description="Admin level 3 (country/region level)")

    class Config:
        json_schema_extra = {
            "example": {
                "admin_level_high": "Ullensaker",
                "admin_level_mid": "Akershus",
                "admin_level_low": "Norway"
            }
        }


class ErrorResponse(BaseModel):
    """Standard error response"""
    message: str = Field(..., description="Human-readable error message")
    code: Optional[str] = Field(None, description="Machine-readable error code")
    details: Optional[dict] = Field(None, description="Additional error details")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Invalid coordinates provided",
                "code": "INVALID_PARAMETERS"
            }
        }

