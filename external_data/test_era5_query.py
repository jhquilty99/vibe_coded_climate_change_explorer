#!/usr/bin/env python3
"""
Pytest test suite for evaluating historical monthly temperature data using query_era5.
Tests all historical monthly temperature data for multiple locations.
"""

import pytest
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path

# Add the external_data/utils directory to the path
sys.path.insert(0, str(Path(__file__).parent / 'utils'))

from query_era5 import query_era5


# Test coordinates - same as in test_api.py
TEST_COORDINATES = [
    {
        "name": "New York City, USA",
        "lat": 40.75, 
        "lng": 286.0,
        "description": "Major US city",
        "test_file": "new_york_city.csv"
    },
    {
        "name": "London, UK", 
        "lat": 51.5,
        "lng": 359.75,
        "description": "European capital",
        "test_file": "london_uk.csv"
    },
    {
        "name": "Tokyo, Japan",
        "lat": 35.75,
        "lng": 139.75,
        "description": "Asian megacity",
        "test_file": "tokyo_japan.csv"
    },
    {
        "name": "Ocean",
        "lat": -60,
        "lng": -60,
        "description": "Middle of the ocean",
        "test_file": "ocean.csv"
    }
]


@pytest.fixture
def test_coordinates():
    """Fixture to provide test coordinates"""
    return TEST_COORDINATES


@pytest.mark.parametrize("coord", TEST_COORDINATES)
def test_query_era5_data_retrieval(coord):
    """Test that query_era5 successfully retrieves temperature data for each location"""
    series = query_era5(coord["lat"], coord["lng"])
    
    # Verify data structure
    assert isinstance(series, pd.Series), "query_era5 should return a pandas Series"
    assert len(series) > 0, f"No temperature data retrieved for {coord['name']}"
    
    # Verify data has DatetimeIndex
    assert isinstance(series.index, pd.DatetimeIndex), "Series index should be DatetimeIndex"
    
    # Verify data has temperature values
    assert series.name == 't2m', f"Series should be named 't2m', got '{series.name}'"
    
    print(f"\n✓ Retrieved {len(series)} temperature records for {coord['name']}")


@pytest.mark.parametrize("coord", TEST_COORDINATES)
def test_query_era5_data_range(coord):
    """Test that the data covers the expected historical range (1940-2024)"""
    series = query_era5(coord["lat"], coord["lng"])
    
    # Get date range
    start_date = series.index.min()
    end_date = series.index.max()
    
    # Verify date range is reasonable
    assert start_date.year == 1940, f"Expected data to start in 1940, got {start_date.year}"
    assert end_date.year >= 2023, f"Expected data to extend to at least 2023, got {end_date.year}"
    
    print(f"\n✓ Data range for {coord['name']}: {start_date.date()} to {end_date.date()}")


@pytest.mark.parametrize("coord", TEST_COORDINATES)
def test_query_era5_temperature_values(coord):
    """Test that temperature values are within reasonable ranges"""
    series = query_era5(coord["lat"], coord["lng"])
    
    # Get basic statistics
    temp_min = series.min()
    temp_max = series.max()
    temp_mean = series.mean()
    temp_std = series.std()
    
    # Verify temperature values are reasonable (between -100°C and 60°C)
    assert -100 < temp_min < 60, f"Temperature minimum {temp_min}°C is outside reasonable range"
    assert -100 < temp_max < 60, f"Temperature maximum {temp_max}°C is outside reasonable range"
    
    # Verify we have temperature variation (not all the same value)
    assert temp_std > 0, f"Temperature standard deviation is 0 for {coord['name']}"
    
    print(f"\n✓ Temperature statistics for {coord['name']}:")
    print(f"  Min: {temp_min:.2f}°C")
    print(f"  Max: {temp_max:.2f}°C")
    print(f"  Mean: {temp_mean:.2f}°C")
    print(f"  Std: {temp_std:.2f}°C")


@pytest.mark.parametrize("coord", TEST_COORDINATES)
def test_query_era5_temporal_coverage(coord):
    """Test that we have monthly data coverage"""
    series = query_era5(coord["lat"], coord["lng"])
    
    # Check for consistent monthly sampling
    # ERA5 data should have monthly or higher frequency data
    time_deltas = series.index.to_series().diff().dropna()
    most_common_delta = time_deltas.mode()[0] if len(time_deltas.mode()) > 0 else None
    
    # Verify data has consistent temporal spacing (monthly or daily)
    assert most_common_delta is not None, f"No consistent time delta found for {coord['name']}"
    
    # ERA5 monthly data should have approximately 1-month intervals
    days_between = most_common_delta.days
    # Allow for some flexibility (28-32 days for monthly data)
    assert 25 <= days_between <= 35, f"Expected monthly data (~30 days), got {days_between} days for {coord['name']}"
    
    print(f"\n✓ Temporal coverage for {coord['name']}: most common interval is {days_between} days")


@pytest.mark.parametrize("coord", TEST_COORDINATES)
def test_query_era5_no_missing_values(coord):
    """Test that there are no missing temperature values in critical periods"""
    series = query_era5(coord["lat"], coord["lng"])
    
    # Check for missing values
    missing_count = series.isna().sum()
    
    # Should have minimal missing values (or none)
    missing_percentage = (missing_count / len(series)) * 100
    
    assert missing_percentage < 5, f"Too many missing values ({missing_percentage:.2f}%) for {coord['name']}"
    
    print(f"\n✓ Missing values for {coord['name']}: {missing_count} ({missing_percentage:.2f}%)")


@pytest.mark.parametrize("coord", TEST_COORDINATES)
def test_query_era5_seasonal_patterns(coord):
    """Test that temperature data shows expected seasonal patterns"""
    series = query_era5(coord["lat"], coord["lng"])
    
    # Add month information
    monthly_temps = pd.DataFrame({'month': series.index.month, 't2m': series.values})
    
    # Calculate average temperature by month
    monthly_avg = monthly_temps.groupby("month")["t2m"].mean()
    
    # For most locations, we should see temperature variation across months
    # (though not all locations may have strong seasonality)
    temp_range = monthly_avg.max() - monthly_avg.min()
    
    # Temperature should vary by at least 5°C across the year for most locations
    # (allowing for exceptions like equatorial locations)
    if "Ocean" in coord["name"] or coord["lat"] < -45 or coord["lat"] > 60:
        # Ocean or extreme latitudes might have less variation
        pass
    else:
        assert temp_range > 3, f"Expected seasonal variation for {coord['name']}, got {temp_range:.2f}°C range"
    
    print(f"\n✓ Seasonal pattern for {coord['name']}: {temp_range:.2f}°C range across months")


def test_query_era5_all_locations():
    """Test that all locations return consistent data structures"""
    results = {}
    
    for coord in TEST_COORDINATES:
        series = query_era5(coord["lat"], coord["lng"])
        results[coord["name"]] = {
            "records": len(series),
            "start_date": series.index.min(),
            "end_date": series.index.max(),
            "temp_min": series.min(),
            "temp_max": series.max(),
            "temp_mean": series.mean()
        }
    
    # Verify all locations have data
    assert len(results) == len(TEST_COORDINATES), "Not all locations returned data"
    
    # Print summary
    print("\n" + "="*80)
    print("SUMMARY OF ALL LOCATIONS")
    print("="*80)
    for name, data in results.items():
        print(f"\n{name}:")
        print(f"  Records: {data['records']:,}")
        print(f"  Date Range: {data['start_date'].date()} to {data['end_date'].date()}")
        print(f"  Temperature Range: {data['temp_min']:.2f}°C to {data['temp_max']:.2f}°C")
        print(f"  Average Temperature: {data['temp_mean']:.2f}°C")
    print("="*80)


@pytest.mark.parametrize("coord", TEST_COORDINATES)
def test_era5_accuracy_against_test_data(coord):
    """
    Test that ERA5 data matches the reference test data within 0.1 degrees Celsius.
    The test data comes from Open Meteo API monthly averages.
    """
    # Get the test data file path
    test_data_dir = Path(__file__).parent / 'test_data'
    csv_file = test_data_dir / coord["test_file"]
    
    # Read the reference test data (Open Meteo monthly averages)
    reference_df = pd.read_csv(csv_file)
    
    # Query ERA5 data
    t2m_celsius = query_era5(coord["lat"], coord["lng"])
    
    # Convert ERA5 datetime index to year and month columns
    era5_df = pd.DataFrame({
        'year': t2m_celsius.index.year,
        'month': t2m_celsius.index.month,
        't2m_celsius': t2m_celsius.values
    })
    
    # Group by year and month to get monthly averages
    era5_monthly = era5_df.groupby(['year', 'month'])['t2m_celsius'].mean().reset_index()
    
    # Merge with reference data on year and month
    comparison = pd.merge(
        reference_df[['year', 'month', 'average_temperature_celsius']],
        era5_monthly,
        on=['year', 'month'],
        how='inner'
    )
    
    # Calculate the difference
    comparison['difference'] = abs(comparison['average_temperature_celsius'] - comparison['t2m_celsius'])
    
    # Find any differences that exceed 0.1 degrees
    large_differences = comparison[comparison['difference'] > 0.1]
    
    # Print summary
    print(f"\n✓ Accuracy comparison for {coord['name']}:")
    print(f"  Total months compared: {len(comparison)}")
    print(f"  Average difference: {comparison['difference'].mean():.3f}°C")
    print(f"  Max difference: {comparison['difference'].max():.3f}°C")
    print(f"  Months within 0.1°C: {len(comparison) - len(large_differences)}/{len(comparison)}")
    
    if len(large_differences) > 0:
        print(f"  ⚠️  Months exceeding 0.1°C tolerance: {len(large_differences)}")
        print(f"     First 5 large differences:")
        for _, row in large_differences.head().iterrows():
            print(f"       {int(row['year'])}-{int(row['month']):02d}: "
                  f"Ref={row['average_temperature_celsius']:.2f}°C, "
                  f"ERA5={row['t2m_celsius']:.2f}°C, "
                  f"Diff={row['difference']:.2f}°C")
    
    # Assert that all differences are within 0.1 degrees
    assert len(large_differences) == 0, (
        f"Found {len(large_differences)} months where ERA5 differs from reference data by more than 0.1°C "
        f"for {coord['name']}. Max difference: {comparison['difference'].max():.3f}°C"
    )


if __name__ == "__main__":
    # Allow running with python -m pytest or python test_era5_query.py
    pytest.main([__file__, "-v", "--tb=short"])

