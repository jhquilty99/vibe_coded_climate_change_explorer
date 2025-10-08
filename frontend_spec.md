## **Frontend Requirements: Interactive Weather Map**

This document outlines the high-level design and functional requirements for an interactive weather map application. The application has two primary states: a **Default View** and a **Selected Location View**.

---

### **1. Overall Layout & States**

* **Default View:** The initial state of the application should be a full-width, interactive map.
* **Selected Location View:** When a location is selected, the layout should transition to a two-column view.
    * **Left Column:** A fixed-width information panel displaying detailed weather data for the selected location. This panel should overlay a portion of the map.
    * **Right Column:** The interactive map, with the selected location centered or clearly in view.

---

### **2. Map Component (Both Views)**


* **Interactivity:** The map must be pannable and zoomable. Standard zoom-in (+) and zoom-out (-) controls should be present.
* **Search Functionality:**
    * A search bar should be present at the top of the map view.
    * It should include a search icon and placeholder text (e.g., "Search for locations...").
    * User input should generate a list of location suggestions. Selecting a location triggers the **Selected Location View**.
* **Location Marker:** In the **Selected Location View**, a distinct pin or marker must be placed on the map to indicate the selected coordinates.
* **Limits:** Map only displays longitudes between -180 and 180 and latitudes between -90 and 90. 

---

### **3. Information Panel (Selected Location View Only)**

This panel appears on the left side of the screen when a location is active. It is composed of several distinct modules and should be dismissible (e.g., via an 'x' icon).

* **Header Module:**
    * **Location Name:** Display the primary name (e.g., "Houston, United States") in a large font.
    * **Region/Coordinates:** Display the sub-region (e.g., "Missouri") and the geographical coordinates.
    * **Last Updated:** A timestamp indicating when the data was last refreshed.
    * **Close Button:** An 'x' icon to close the panel and return to the **Default View**.

* **Current Temperature Module:**
    * A large, clear weather-related icon (e.g., a thermometer).
    * The current temperature displayed prominently.
    * The unit of measurement (e.g., °C).

* **Historical Average Module:**
    * A clear title, such as "vs. Historical Average".
    * The deviation from the historical average (e.g., "-3.6°C").
    * The historical average temperature for context (e.g., "Historical Average: 17.1°C").
    * A simple text description of the deviation (e.g., "Slightly Colder").
    * A horizontal, color-graded bar representing the temperature difference from the historical average, with a marker indicating the current temperature's position on that scale.

* **Annual Trend Chart Module:**
    * A title, such as "Annual Temperature Trend".
    * A simple line chart visualizing the temperature trend over multiple years.
    * The Y-axis should be labeled with Temperature (°C) and the X-axis with the Year.

---

### **4. Backend Integration**

The frontend should integrate with the Climate Change Explorer API to retrieve location and climate data. All API endpoints are prefixed with `/api/v1/` and accept latitude (`lat`) and longitude (`lng`) query parameters.

* **Backend Server**
    * IP: http://188.245.105.237:8000

* **Location Name and Coordinates:**
    * **Endpoint:** `GET /api/v1/reverse-geocode`
    * **Parameters:** `lat`, `lng`
    * **Purpose:** Convert selected coordinates to a human-readable location name.
    * **Usage:** When a location is selected on the map, call this endpoint to populate the Header Module with the city, state (optional), and country information.
    * **Response Fields:** `city`, `state` (optional), `country`

* **Current Temperature and Historical Average:**
    * **Endpoint:** `GET /api/v1/temperature-summary`
    * **Parameters:** `lat`, `lng`
    * **Purpose:** Retrieve current temperature, historical baseline, and temperature deviation.
    * **Usage:** Populate both the Current Temperature Module and the Historical Average Module.
    * **Response Fields:**
        * `current_temperature` → Display in Current Temperature Module
        * `earliest_temperature` → Use as historical average reference
        * `temperature_difference` → Display the deviation and determine if it's warmer/colder
        * `updated_at` → Display in the Header Module as "Last Updated"

* **Annual Temperature Trend:**
    * **Endpoint:** `GET /api/v1/temperature-graph`
    * **Parameters:** `lat`, `lng`
    * **Purpose:** Retrieve year-by-year temperature data for chart visualization.
    * **Usage:** Populate the Annual Trend Chart Module with historical temperature trends.
    * **Response Format:** Array of objects, each containing:
        * `year` → X-axis values
        * `avg_mean_temperature` → Y-axis values

* **Error Handling:**
    * All endpoints may return error responses (400, 404, 500).
    * The frontend should gracefully handle errors and display user-friendly messages when:
        * Invalid coordinates are provided (400)
        * Location data is not found (404)
        * Server errors occur (500)
    * Loading states should be displayed while API requests are in progress.

* **API Coordination:**
    * When a location is selected, the frontend should make parallel requests to all three endpoints (`/reverse-geocode`, `/temperature-summary`, `/temperature-graph`) to minimize loading time.
    * The information panel should display loading indicators for each module until its corresponding data is received.
    * All API requests should use the same coordinate pair to ensure data consistency.