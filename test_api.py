#!/usr/bin/env python3
"""
Pytest test suite for Climate Change Explorer API endpoints.
Tests both reverse-geocode and temperature endpoints with different coordinates.
"""

import pytest
import httpx
import json
from datetime import datetime
from typing import Dict, Any, List, Tuple


# Test configuration
BASE_URL = "http://localhost:8000"
    
    # Test coordinates - three different locations
TEST_COORDINATES = [
        {
            "name": "New York City, USA",
            "lat": 40.7128,
            "lng": -74.0060,
            "description": "Major US city"
        },
        {
            "name": "London, UK", 
            "lat": 51.5074,
            "lng": -0.1278,
            "description": "European capital"
        },
        {
            "name": "Tokyo, Japan",
            "lat": 35.6762,
            "lng": 139.6503,
            "description": "Asian megacity"
        },
        {
            "name": "Tibesti Est, Chad",
            "lat": 19.11,
            "lng": 19.43,
            "description": "Middle of Nowhere Chad"
        },
        {
            "name": "Chelyabinsk, Russia",
            "lat": 55.43,
            "lng": 60.72,
            "description": "Middle of Nowhere Russia"
        },
        {
            "name": "Yukon, Canada",
            "lat": 64.65,
            "lng": -133.87,
            "description": "Middle of Nowhere Northern Canada"
        },
        {
            "name": "Ocean",
            "lat": -60,
            "lng": -60,
            "description": "Middle of the ocean"
        }
    ]
    

@pytest.fixture
def api_client():
    """Fixture to provide an async HTTP client for API testing"""
    return httpx.AsyncClient(timeout=30.0)


@pytest.fixture
def test_coordinates():
    """Fixture to provide test coordinates"""
    return TEST_COORDINATES


@pytest.mark.asyncio
async def test_health_check(api_client):
    """Test health check endpoint"""
    async with api_client as client:
        response = await client.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"


@pytest.mark.asyncio
@pytest.mark.parametrize("coord,expected_high,expected_mid,expected_low", [
    (TEST_COORDINATES[0], "New York County", "New York", "United States"),  # NYC
    (TEST_COORDINATES[1], "City of Westminster", "England", "United Kingdom"),    # London
    (TEST_COORDINATES[2], "Suginami", "Tokyo", "Japan"),  # Tokyo
    (TEST_COORDINATES[3], "Tibesti", "Tibesti", "Chad"),  # Tibesti Est
    (TEST_COORDINATES[4], "Argayashsky District", "Chelyabinsk Oblast", "Russia"),  # Chelyabinsk
    (TEST_COORDINATES[5], "Yukon", "Yukon", "Canada"),  # Yukon
    (TEST_COORDINATES[6], "Ocean", "Ocean", "Ocean"),  # Ocean
])
async def test_reverse_geocode(api_client, coord, expected_high, expected_mid, expected_low):
    """Test reverse geocoding endpoint with different coordinates and validate specific admin level data"""
    async with api_client as client:
        url = f"{BASE_URL}/api/v1/reverse-geocode"
        params = {"lat": coord["lat"], "lng": coord["lng"]}
        
        response = await client.get(url, params=params)
        assert response.status_code == 200
        
        data = response.json()
        
        # Check that the response has the new admin_level structure
        assert "admin_level_high" in data
        assert "admin_level_mid" in data  
        assert "admin_level_low" in data
        
        # All admin levels should be populated
        assert data["admin_level_high"] is not None, f"High admin level should be populated for {coord['name']}"
        assert data["admin_level_mid"] is not None, f"Mid admin level should be populated for {coord['name']}"
        assert data["admin_level_low"] is not None, f"Low admin level should be populated for {coord['name']}"
        
        # Validate specific expected values
        assert data["admin_level_high"] == expected_high, (
            f"High admin level mismatch for {coord['name']}: "
            f"expected '{expected_high}', got '{data['admin_level_high']}'"
        )
        assert data["admin_level_mid"] == expected_mid, (
            f"Mid admin level mismatch for {coord['name']}: "
            f"expected '{expected_mid}', got '{data['admin_level_mid']}'"
        )
        assert data["admin_level_low"] == expected_low, (
            f"Low admin level mismatch for {coord['name']}: "
            f"expected '{expected_low}', got '{data['admin_level_low']}'"
        )
        
        # Log the response for debugging
        print(f"\nAdmin levels for {coord['name']}:")
        print(f"  High (9-10): {data['admin_level_high']} ✓")
        print(f"  Mid (5-8): {data['admin_level_mid']} ✓")
        print(f"  Low (3-4): {data['admin_level_low']} ✓")


@pytest.mark.asyncio
@pytest.mark.parametrize("coord,expected_earliest_temp", [
    (TEST_COORDINATES[0], 10.48),  # NYC
    (TEST_COORDINATES[1], 10.04),  # London
    (TEST_COORDINATES[2], 13.90),  # Tokyo
    (TEST_COORDINATES[3], 24.60),  # Tibesti Est
    (TEST_COORDINATES[4], 1.18),  # Chelyabinsk
    (TEST_COORDINATES[5], -4.64),  # Yukon
    (TEST_COORDINATES[6], 0.23),  # Ocean
])
async def test_temperature_summary(api_client, coord, expected_earliest_temp):
    """Test temperature summary part of the new /temperature endpoint with different coordinates and validate earliest temperature values"""
    async with api_client as client:
        url = f"{BASE_URL}/api/v1/temperature"
        params = {"lat": coord["lat"], "lng": coord["lng"]}
        
        response = await client.get(url, params=params)
        assert response.status_code == 200
        
        data = response.json()
        assert "summary" in data
        assert "yearly_data" in data
        
        summary = data["summary"]
        assert "current_temperature" in summary
        assert "earliest_temperature" in summary
        assert "temperature_difference" in summary
        assert "updated_at" in summary
        
        # Validate temperature data types
        assert isinstance(summary["current_temperature"], (int, float))
        assert isinstance(summary["earliest_temperature"], (int, float))
        assert isinstance(summary["temperature_difference"], (int, float))
        
        # Validate earliest temperature values with margin of error
        actual_temp = summary["earliest_temperature"]
        margin_of_error = 0.1
        
        assert abs(actual_temp - expected_earliest_temp) <= margin_of_error, (
            f"Earliest temperature for {coord['name']} is {actual_temp}°C, "
            f"expected {expected_earliest_temp}°C (±{margin_of_error}°C)"
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("coord", TEST_COORDINATES)
async def test_temperature_graph(api_client, coord):
    """Test temperature yearly data part of the new /temperature endpoint with different coordinates"""
    async with api_client as client:
        url = f"{BASE_URL}/api/v1/temperature"
        params = {"lat": coord["lat"], "lng": coord["lng"]}
        
        response = await client.get(url, params=params)
        assert response.status_code == 200
        
        data = response.json()
        assert "summary" in data
        assert "yearly_data" in data
        
        yearly_data = data["yearly_data"]
        assert isinstance(yearly_data, list)
        assert len(yearly_data) > 0
        
        # Validate data structure
        for year_data in yearly_data:
            assert "year" in year_data
            assert "avg_mean_temperature" in year_data
            assert isinstance(year_data["year"], int)
            assert isinstance(year_data["avg_mean_temperature"], (int, float))


@pytest.mark.asyncio
async def test_invalid_coordinates(api_client):
    """Test API behavior with invalid coordinates"""
    async with api_client as client:
        # Test with coordinates outside valid range
        invalid_coords = [
            (91.0, 0.0),  # Invalid latitude
            (0.0, 181.0),  # Invalid longitude
            (-91.0, 0.0),  # Invalid latitude
            (0.0, -181.0),  # Invalid longitude
        ]
        
        for lat, lng in invalid_coords:
            # Test reverse geocoding with invalid coordinates
            url = f"{BASE_URL}/api/v1/reverse-geocode"
            params = {"lat": lat, "lng": lng}
            
            response = await client.get(url, params=params)
            # Should return 422 Unprocessable Entity for invalid coordinates
            assert response.status_code == 422


@pytest.mark.asyncio
async def test_missing_parameters(api_client):
    """Test API behavior with missing required parameters"""
    async with api_client as client:
        # Test reverse geocoding without parameters
        url = f"{BASE_URL}/api/v1/reverse-geocode"
        response = await client.get(url)
        assert response.status_code == 422  # Unprocessable Entity
        
        # Test temperature endpoint without parameters
        url = f"{BASE_URL}/api/v1/temperature"
        response = await client.get(url)
        assert response.status_code == 422  # Unprocessable Entity


@pytest.mark.asyncio
@pytest.mark.parametrize("coord", TEST_COORDINATES)
async def test_1940_temperature_consistency(api_client, coord):
    """Test that 1940 average temperature from yearly_data matches earliest temperature from summary in the new /temperature endpoint"""
    async with api_client as client:
        # Get temperature data from the new combined endpoint
        url = f"{BASE_URL}/api/v1/temperature"
        params = {"lat": coord["lat"], "lng": coord["lng"]}
        
        response = await client.get(url, params=params)
        assert response.status_code == 200
        data = response.json()
        
        # Get earliest temperature from summary
        earliest_temp = data["summary"]["earliest_temperature"]
        
        # Find 1940 data in the yearly_data
        temp_1940 = None
        for year_data in data["yearly_data"]:
            if year_data["year"] == 1940:
                temp_1940 = year_data["avg_mean_temperature"]
                break
        
        assert temp_1940 is not None, f"No temperature data found for 1940 for {coord['name']}"
        
        # Validate that 1940 temperature matches earliest temperature
        margin_of_error = 0.01  # Small margin for floating point precision
        assert abs(temp_1940 - earliest_temp) <= margin_of_error, (
            f"Temperature mismatch for {coord['name']}: "
            f"1940 temperature is {temp_1940}°C, "
            f"earliest temperature is {earliest_temp}°C"
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("coord,expected_slope,expected_intercept", [
    (TEST_COORDINATES[0], 0.01370, -15.70932),  # New York
    (TEST_COORDINATES[1], 0.01672, -22.81),     # London
    (TEST_COORDINATES[2], 0.01681, -18.9),      # Tokyo
])
async def test_temperature_regression_line(api_client, coord, expected_slope, expected_intercept):
    """Test temperature regression line (slope and intercept) for the first three locations with 10% margin of error"""
    async with api_client as client:
        url = f"{BASE_URL}/api/v1/temperature"
        params = {"lat": coord["lat"], "lng": coord["lng"]}
        
        response = await client.get(url, params=params)
        assert response.status_code == 200
        
        data = response.json()
        assert "trend" in data
        
        trend = data["trend"]
        assert "slope" in trend
        assert "intercept" in trend
        assert "r_squared" in trend
        
        # Validate data types
        assert isinstance(trend["slope"], (int, float))
        assert isinstance(trend["intercept"], (int, float))
        assert isinstance(trend["r_squared"], (int, float))
        
        # Validate slope and intercept with 10% margin of error
        actual_slope = trend["slope"]
        actual_intercept = trend["intercept"]
        margin_of_error = 0.10  # 10% margin of error
        
        slope_error = abs(actual_slope - expected_slope) / abs(expected_slope) if expected_slope != 0 else abs(actual_slope)
        intercept_error = abs(actual_intercept - expected_intercept) / abs(expected_intercept) if expected_intercept != 0 else abs(actual_intercept)
        
        assert slope_error <= margin_of_error, (
            f"Slope error for {coord['name']} exceeds 10% margin: "
            f"expected {expected_slope}, got {actual_slope} "
            f"(error: {slope_error:.2%})"
        )
        
        assert intercept_error <= margin_of_error, (
            f"Intercept error for {coord['name']} exceeds 10% margin: "
            f"expected {expected_intercept}, got {actual_intercept} "
            f"(error: {intercept_error:.2%})"
        )
        
        # Log the regression data for debugging
        print(f"\nRegression line for {coord['name']}:")
        print(f"  Slope: {actual_slope:.6f} (expected: {expected_slope:.6f}) ✓")
        print(f"  Intercept: {actual_intercept:.2f} (expected: {expected_intercept:.2f}) ✓")
        print(f"  R-squared: {trend['r_squared']:.4f}")


@pytest.mark.asyncio
async def test_api_response_times(api_client):
    """Test that API responses are within acceptable time limits"""
    import time
    
    async with api_client as client:
        coord = TEST_COORDINATES[0]  # Use first coordinate for timing tests
        
        # Test reverse geocoding response time
        start_time = time.time()
        url = f"{BASE_URL}/api/v1/reverse-geocode"
        params = {"lat": coord["lat"], "lng": coord["lng"]}
        response = await client.get(url, params=params)
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 5.0  # Should respond within 5 seconds
        
        # Test temperature endpoint response time
        start_time = time.time()
        url = f"{BASE_URL}/api/v1/temperature"
        response = await client.get(url, params=params)
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 10.0  # Temperature data might take longer


if __name__ == "__main__":
    # Allow running with python -m pytest or python test_api.py
    pytest.main([__file__, "-v", "--tb=short"])
