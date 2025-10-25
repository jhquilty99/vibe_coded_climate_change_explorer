# Climate Change Explorer API

A FastAPI-based backend service providing climate data and reverse geocoding capabilities.

## Features

- **Temperature Summary**: Get current temperature, earliest recorded temperature, and temperature difference for any location
- **Temperature Graph**: Retrieve historical temperature data by year from 1940 to present
- **Reverse Geocoding**: Convert coordinates to human-readable location information

## Tech Stack

- **FastAPI**: Modern, fast web framework for building APIs
- **httpx**: Async HTTP client for external API calls
- **Pydantic**: Data validation using Python type hints
- **Uvicorn**: ASGI server for running the application

## External APIs Used

- **Open-Meteo Archive API**: Historical weather data from 1940 onwards
- **Nominatim (OpenStreetMap)**: Reverse geocoding service

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd vibe_coded_climate_change_explorer
```

2. Create a virtual environment:
```bash
python -m venv venv
```

3. Activate the virtual environment:
- Windows:
  ```bash
  venv\Scripts\activate
  ```
- macOS/Linux:
  ```bash
  source venv/bin/activate
  ```

4. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

### Development Mode

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 5000
```

Or simply:
```bash
python -m app.main
```

### Production Mode

```bash
uvicorn app.main:app --host 0.0.0.0 --port 5000 --workers 4
```

## API Endpoints

### Temperature Summary
```
GET /api/v1/temperature-summary?lat=33.0&lng=-87.0
```

Returns current temperature, earliest recorded temperature, and the difference.

### Temperature Graph
```
GET /api/v1/temperature-graph?lat=33.0&lng=-87.0
```

Returns an array of average temperatures by year.

### Reverse Geocode
```
GET /api/v1/reverse-geocode?lat=33.0&lng=-87.0
```

Converts coordinates to city, state, and country.

### Health Check
```
GET /health
```

Returns API health status.

## API Documentation

Once the server is running, you can access:

- **Swagger UI**: http://localhost:5000/docs
- **ReDoc**: http://localhost:5000/redoc
- **OpenAPI JSON**: http://localhost:5000/openapi.json

## Project Structure

```
vibe_coded_climate_change_explorer/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── models.py            # Pydantic models
│   └── routes/
│       ├── __init__.py
│       ├── temperature.py   # Temperature endpoints
│       └── geocoding.py     # Geocoding endpoints
├── requirements.txt         # Python dependencies
├── openapi.yaml            # OpenAPI specification
├── backend_spec.md         # Backend architecture documentation
├── frontend_spec.md        # Frontend specification
└── README.md              # This file
```

## Architecture

This backend follows a simplified architecture where:

1. **API Endpoints** handle all logic directly
2. **External APIs** are called asynchronously using `httpx`
3. **No intermediate layers** - endpoints are responsible for:
   - Request validation
   - Fetching data from external APIs
   - Data processing and aggregation
   - Error handling
   - Response serialization

## Error Handling

The API returns structured error responses:

```json
{
  "message": "Human-readable error message",
  "code": "MACHINE_READABLE_CODE",
  "details": {}
}
```

Common HTTP status codes:
- `200`: Success
- `400`: Invalid parameters
- `404`: Location not found
- `500`: Internal server error
- `503`: External API unavailable

## CORS

CORS is enabled for all origins in development. For production, update the `allow_origins` in `app/main.py` to restrict access to specific domains.

## Development

### Adding New Endpoints

1. Create a new router in `app/routes/`
2. Define Pydantic models in `app/models.py`
3. Include the router in `app/main.py`

### Testing

You can test the endpoints using:
- The built-in Swagger UI at `/docs`
- curl:
  ```bash
  curl "http://localhost:5000/api/v1/temperature-summary?lat=33.0&lng=-87.0"
  ```
- Any HTTP client (Postman, Insomnia, etc.)

## License

This project is open source and available under the MIT License.

