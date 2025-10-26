import requests
import csv
from datetime import datetime
from collections import defaultdict

def get_monthly_temperature_averages(lat, long, file_location):
    """
    Fetch historical temperature data from Open Meteo Archive API,
    calculate monthly averages, and save to CSV.
    
    Args:
        lat (float): Latitude
        long (float): Longitude  
        file_location (str): Path where the CSV file should be saved
    """
    # Construct API URL
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        'latitude': lat,
        'longitude': long,
        'start_date': '1940-01-01',
        'end_date': '2024-12-31',
        'daily': 'temperature_2m_mean'
    }
    
    # Fetch data from API
    print(f"Fetching temperature data for coordinates ({lat}, {long})...")
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    
    # Extract daily data
    daily_data = data.get('daily', {})
    times = daily_data.get('time', [])
    temperatures = daily_data.get('temperature_2m_mean', [])
    
    if not times or not temperatures:
        raise ValueError("No data returned from API")
    
    print(f"Found {len(times)} days of data")
    
    # Group temperatures by year and month, calculating averages
    monthly_temps = defaultdict(lambda: defaultdict(list))
    
    for time_str, temp in zip(times, temperatures):
        if temp is not None:  # Skip missing data
            date = datetime.fromisoformat(time_str)
            year = date.year
            month = date.month
            monthly_temps[year][month].append(temp)
    
    # Calculate monthly averages and prepare data for CSV
    csv_rows = []
    for year in sorted(monthly_temps.keys()):
        for month in sorted(monthly_temps[year].keys()):
            temps = monthly_temps[year][month]
            avg_temp = sum(temps) / len(temps)
            csv_rows.append({
                'year': year,
                'month': month,
                'average_temperature_celsius': round(avg_temp, 2),
                'days_with_data': len(temps)
            })
    
    # Write to CSV
    print(f"Saving monthly averages to {file_location}...")
    with open(file_location, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['year', 'month', 'average_temperature_celsius', 'days_with_data'])
        writer.writeheader()
        writer.writerows(csv_rows)
    
    print(f"Successfully saved {len(csv_rows)} monthly averages to {file_location}")
    return csv_rows


if __name__ == "__main__":
    # Example usage
    TEST_COORDINATES = [
        {
            "name": "new_york_city",
            "lat": 40.75, 
            "lng": 286.0-360,
        },
        {
            "name": "london_uk", 
            "lat": 51.5,
            "lng": 359.75-360,
        },
        {
            "name": "tokyo_japan",
            "lat": 35.75,
            "lng": 139.75,
        },
        {
            "name": "ocean",
            "lat": -60,
            "lng": -60
        }
    ]
    for coord in TEST_COORDINATES:
        get_monthly_temperature_averages(
            lat=coord["lat"],
            long=coord["lng"],
            file_location=f"test_data/{coord['name']}.csv"
        )
