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
    Converts latitude and longitude coordinates into administrative level
    information using OpenStreetMap's geocodejson format.
    Returns admin levels: high (10-12), mid (5-9), and low (3).
    """
    try:
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            "lat": lat,
            "lon": lng,
            "zoom": 18,
            "format": "geocodejson"
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
            return GeocodingResponse(
                admin_level_high="Ocean",
                admin_level_mid="Ocean",
                admin_level_low="Ocean"
            )
        
        # Extract features from geocodejson response
        features = data.get("features", [])
        if not features:
            raise HTTPException(
                status_code=404,
                detail={"message": "Location not found for the given coordinates", "code": "LOCATION_NOT_FOUND"}
            )
        
        # Get the first feature (most relevant result)
        feature = features[0]
        properties = feature.get("properties", {})
        geocoding = properties.get("geocoding", {})
        admin = geocoding.get("admin", {})

        admin_level_low = geocoding.get("country", "Unknown")
        
        # Extract admin levels based on the mapping:
        # admin_level_high: level 9 or 10 (city/town level)
        # admin_level_mid: level 5, 6, 7, or 8 (county/state/province level)  
        # admin_level_low: level 3 or 4 (country/region level)
        
        admin_level_high = "Unknown"
        admin_level_mid = "Unknown"
        
        # Find admin_level_high (city/town) from levels 9-10
        for level in [9, 8, 7, 6]:
            level_key = f"level{level}"
            if level_key in admin and admin[level_key]:
                admin_level_high = admin[level_key]
                
        # Find admin_level_mid (county/state) from levels 5-8
        for level in [5, 4]:
            level_key = f"level{level}"
            if level_key in admin and admin[level_key]:
                admin_level_mid = admin[level_key]

        if admin_level_high == "Unknown":
            admin_level_high = admin_level_mid
        
        return GeocodingResponse(
            admin_level_high=admin_level_high,
            admin_level_mid=admin_level_mid,
            admin_level_low=admin_level_low
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

