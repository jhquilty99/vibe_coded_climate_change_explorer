## Simplified Climate API Architecture

This architecture connects API endpoints directly to external data sources.

The core idea is that each API endpoint is self-contained and responsible for fetching, processing, and returning its specific data.

### Simplified Architecture Diagram

The system is reduced to two primary layers: the API endpoints that clients interact with and the external APIs that provide the raw data.

```
┌───────────────────────────────────┐
│           API Endpoints           │   ← FastAPI routes handle all logic
└───────────────────────────────────┘
                │
                │ (Direct HTTP calls via httpx)
                ↓
┌───────────────────────────────────┐
│           External APIs           │   ← Open-Meteo (Weather) & Nominatim (Geocoding)
└───────────────────────────────────┘
```

-----

### Components

#### 1\. API Endpoints

The API endpoints are the core of the application and handle all the work. They are defined using a web framework like **FastAPI**.

**Responsibilities:**

  * **Receive Requests:** Accept HTTP requests from a client (e.g., a web browser).
  * **Validate Input:** Ensure coordinates (`latitude`, `longitude`) are valid.
  * **Fetch Data:** Make direct, asynchronous HTTP calls to the necessary external API (e.g., Open-Meteo) using a library like **`httpx`**.
  * **Process Data:** Aggregate and transform the raw JSON response from the external API into a useful format (e.g., calculating yearly averages from daily data points).
  * **Handle Errors:** Catch network or API errors and return an appropriate HTTP error status (e.g., 503 Service Unavailable).
  * **Return Response:** Send the final, structured JSON data back to the client using **Pydantic models** for validation and serialization.

#### 2\. External APIs

These are the third-party services that provide the raw data.

  * **Open-Meteo API**: The source for all historical temperature data.
  * **Nominatim API**: The source for converting geographic coordinates into a human-readable address (reverse geocoding).

Details:
* https://archive-api.open-meteo.com/v1/archive - Historical weather data (back to 1940)
Example input:
https://archive-api.open-meteo.com/v1/archive?latitude=52.52&longitude=13.41&start_date=2025-09-22&end_date=2025-10-06&daily=temperature_2m_mean
Example output: 
{"latitude":52.54833,"longitude":13.407822,"generationtime_ms":0.062465667724609375,"utc_offset_seconds":0,"timezone":"GMT","timezone_abbreviation":"GMT","elevation":38.0,"daily_units":{"time":"iso8601","temperature_2m_mean":"°C"},"daily":{"time":["2025-09-22","2025-09-23","2025-09-24","2025-09-25","2025-09-26","2025-09-27","2025-09-28","2025-09-29","2025-09-30","2025-10-01","2025-10-02","2025-10-03","2025-10-04","2025-10-05","2025-10-06"],"temperature_2m_mean":[12.5,10.9,10.9,11.3,12.2,13.1,12.1,11.2,9.2,8.7,8.6,8.4,9.6,11.4,12.0]}}

* https://nominatim.openstreetmap.org/reverse 
Example input:
https://nominatim.openstreetmap.org/reverse?lat=10&lon=10&zoom=18&format=jsonv2
Example output:
{"place_id":36778897,"licence":"Data © OpenStreetMap contributors, ODbL 1.0. http://osm.org/copyright","osm_type":"relation","osm_id":3722465,"lat":"10.0110602","lon":"9.9623522","category":"boundary","type":"administrative","place_rank":16,"importance":0.18671687418936442,"addresstype":"city_district","name":"Mun-Munsal","display_name":"Mun-Munsal, Bauchi, Bauchi State, Nigeria","address":{"city_district":"Mun-Munsal","city":"Bauchi","state":"Bauchi State","ISO3166-2-lvl4":"NG-BA","country":"Nigeria","country_code":"ng"},"boundingbox":["9.8953012","10.1286713","9.8773655","10.0987622"]}