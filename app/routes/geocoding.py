from fastapi import APIRouter, HTTPException, Query
import httpx
from app.models import GeocodingResponse, ErrorResponse

router = APIRouter(prefix="/api/v1", tags=["Geocoding"])


@router.get("/reverse-geocode", response_model=GeocodingResponse)
async def reverse_geocode(
    lat: float = Query(..., ge=-90, le=90, description="Latitude coordinate"),
    lng: float = Query(..., ge=-180, le=180, description="Longitude coordinate")
):
    """
    Converts latitude and longitude coordinates into human-readable
    location information including city, state, and country.
    """
    try:
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            "lat": lat,
            "lon": lng,
            "zoom": 18,
            "format": "jsonv2"
        }
        
        headers = {
            "User-Agent": "ClimateChangeExplorer/1.0",
            "Accept-Language": "en"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
        
        # Check if error in response
        if "error" in data:
            raise HTTPException(
                status_code=404,
                detail={"message": "Location not found for the given coordinates", "code": "LOCATION_NOT_FOUND"}
            )
        
        # Extract address information
        address = data.get("address", {})
        
        # Try to get city from various possible fields
        city = (
            address.get("city") or
            address.get("town") or
            address.get("village") or
            address.get("municipality") or
            address.get("city_district") or
            address.get("suburb") or
            address.get("hamlet") or
            "Unknown"
        )
        
        # Try to get state from various possible fields
        state = (
            address.get("state") or
            address.get("province") or
            address.get("region") or
            address.get("county") or
            address.get("state_district") or
            "Unknown"
        )
        
        # Get country
        country = address.get("country", "Unknown")
        
        return GeocodingResponse(
            city=city,
            state=state,
            country=country
        )
        
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=503,
            detail={"message": f"Geocoding service error: {str(e)}", "code": "EXTERNAL_API_ERROR"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"message": f"Internal server error: {str(e)}", "code": "INTERNAL_ERROR"}
        )

