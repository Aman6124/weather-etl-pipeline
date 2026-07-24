"""
Extract module — fetches raw weather data from the Open-Meteo API.

This is the "E" (Extract) step of the ETL pipeline.
We call an external REST API, validate the response, and save the raw JSON
so we always have an audit trail of what was received before any transformation.
"""

import json
from datetime import datetime
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Open-Meteo is free and does not require an API key — ideal for learning.
API_URL = "https://api.open-meteo.com/v1/forecast"

# Pune, India — our initial target city
CITY = "Pune"
LATITUDE = 18.52
LONGITUDE = 73.86

# Weather variables we want from the API's "current" block
CURRENT_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
]

# Project paths (src/ is one level below project root)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"


def build_api_params() -> dict:
    """
    Build query parameters for the Open-Meteo forecast endpoint.

    Returns:
        dict: Parameters passed to requests.get().
    """
    return {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "current": ",".join(CURRENT_VARIABLES),
        "timezone": "Asia/Kolkata",
    }


def fetch_weather_data() -> dict:
    """
    Call the Open-Meteo API and return the JSON response.

    Raises:
        requests.HTTPError: If the API returns a non-2xx status code.
        requests.RequestException: For network or connection problems.
        ValueError: If the response body is not valid JSON.

    Returns:
        dict: Parsed JSON from the API.
    """
    params = build_api_params()

    # timeout prevents the script from hanging if the API is unreachable
    response = requests.get(API_URL, params=params, timeout=30)

    # raise_for_status() turns HTTP errors (404, 500, etc.) into exceptions
    response.raise_for_status()

    try:
        data = response.json()
    except json.JSONDecodeError as exc:
        raise ValueError("API response is not valid JSON.") from exc

    # Open-Meteo includes error details in the JSON body for some failures
    if "error" in data:
        raise ValueError(f"API returned an error: {data.get('reason', data['error'])}")

    return data


def save_raw_json(data: dict) -> Path:
    """
    Save the complete raw API response to data/raw/ with a timestamped filename.

    Timestamped files let us collect multiple snapshots over time without
    overwriting previous runs — useful for learning and for debugging.

    Args:
        data: Raw JSON dictionary from the API.

    Returns:
        Path: Location where the file was saved.
    """
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"weather_{timestamp}.json"
    filepath = RAW_DATA_DIR / filename

    with filepath.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)

    return filepath


def extract_weather() -> Path:
    """
    Main extraction function: fetch weather data and persist raw JSON.

    Returns:
        Path: Path to the saved raw JSON file.

    Raises:
        requests.RequestException: On network or HTTP errors.
        ValueError: On invalid or error JSON responses.
    """
    print(f"Fetching weather data for {CITY} from Open-Meteo API...")

    weather_data = fetch_weather_data()
    output_path = save_raw_json(weather_data)

    print(f"Extraction successful. Raw data saved to: {output_path}")
    return output_path


def main() -> None:
    """Run extraction when this file is executed directly."""
    try:
        extract_weather()
    except requests.RequestException as exc:
        print(f"Extraction failed — network or HTTP error: {exc}")
        raise SystemExit(1) from exc
    except ValueError as exc:
        print(f"Extraction failed — invalid API response: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
