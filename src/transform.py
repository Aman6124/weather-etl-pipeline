"""
Transform module — cleans and structures raw weather JSON into analysis-ready data.

This is the "T" (Transform) step of the ETL pipeline.
We read the latest raw JSON file, extract only the fields we need, validate them,
and save a clean CSV that is ready to load into PostgreSQL.
"""

import json
import math
from datetime import datetime
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CITY = "Pune"

# Final column names used in the processed dataset and database
OUTPUT_COLUMNS = [
    "city",
    "temperature_c",
    "humidity_percent",
    "wind_speed_kmh",
    "recorded_at",
]

# Project paths (src/ is one level below project root)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"


def find_latest_raw_file() -> Path:
    """
    Find the most recently created raw weather JSON file in data/raw/.

    We sort by file modification time so the pipeline always transforms
    the newest extraction result.

    Returns:
        Path: Path to the latest raw JSON file.

    Raises:
        FileNotFoundError: If no raw JSON files exist.
    """
    raw_files = list(RAW_DATA_DIR.glob("weather_*.json"))

    if not raw_files:
        raise FileNotFoundError(
            f"No raw weather JSON files found in {RAW_DATA_DIR}. "
            "Run extract.py first."
        )

    return max(raw_files, key=lambda path: path.stat().st_mtime)


def load_raw_json(filepath: Path) -> dict:
    """
    Read a raw JSON file without modifying it on disk.

    Args:
        filepath: Path to the raw JSON file.

    Returns:
        dict: Parsed JSON content.

    Raises:
        ValueError: If the file cannot be parsed as JSON.
    """
    try:
        with filepath.open("r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in file: {filepath}") from exc


def extract_weather_fields(raw_data: dict) -> dict:
    """
    Map nested API JSON into a flat weather record.

    Open-Meteo stores current readings under the "current" key.
    We add the city name here because the API returns coordinates, not city names.

    Args:
        raw_data: Full raw API response.

    Returns:
        dict: Flat record with business-friendly field names.

    Raises:
        ValueError: If required API fields are missing.
    """
    current = raw_data.get("current")
    if not current:
        raise ValueError("Raw JSON is missing the 'current' weather block.")

    required_api_fields = {
        "temperature_2m": "temperature",
        "relative_humidity_2m": "humidity",
        "wind_speed_10m": "wind_speed",
        "time": "recorded_at",
    }

    record = {"city": CITY}

    for api_field, label in required_api_fields.items():
        value = current.get(api_field)
        if value is None:
            raise ValueError(f"Missing required API field: current.{api_field}")

        if api_field == "time":
            record["recorded_at"] = value
        elif api_field == "temperature_2m":
            record["temperature"] = value
        elif api_field == "relative_humidity_2m":
            record["humidity"] = value
        elif api_field == "wind_speed_10m":
            record["wind_speed"] = value

    return record


def validate_weather_record(record: dict) -> None:
    """
    Validate a single weather record before it enters the DataFrame.

    Data validation catches bad or incomplete data early — before loading
    it into a database where errors are harder to trace.

    Args:
        record: Flat weather record extracted from raw JSON.

    Raises:
        ValueError: If any validation rule fails.
    """
    required_fields = ["city", "temperature", "humidity", "wind_speed", "recorded_at"]

    for field in required_fields:
        if record.get(field) is None or pd.isna(record.get(field)):
            raise ValueError(f"Missing required field: {field}")

    # Conversion alone accepts NaN and infinity, which are not valid readings.
    for field in ("temperature", "humidity", "wind_speed"):
        if not math.isfinite(float(record[field])):
            raise ValueError(
                f"Invalid {field} value: {record[field]}. Expected a finite number."
            )

    humidity = float(record["humidity"])
    if humidity < 0 or humidity > 100:
        raise ValueError(
            f"Invalid humidity value: {humidity}. Expected a value between 0 and 100."
        )


def build_dataframe(record: dict) -> pd.DataFrame:
    """
    Convert a validated weather record into a typed Pandas DataFrame.

    Pandas gives us a familiar table structure for cleaning, validation,
    and exporting to CSV or a SQL database.

    Args:
        record: Validated flat weather record.

    Returns:
        pd.DataFrame: One-row DataFrame with clean column names and types.
    """
    df = pd.DataFrame(
        [
            {
                "city": str(record["city"]),
                "temperature_c": float(record["temperature"]),
                "humidity_percent": float(record["humidity"]),
                "wind_speed_kmh": float(record["wind_speed"]),
                "recorded_at": pd.to_datetime(record["recorded_at"]),
            }
        ]
    )

    # Enforce consistent column order for downstream loading
    return df[OUTPUT_COLUMNS]


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply final DataFrame-level cleaning rules.

    Args:
        df: DataFrame with weather records.

    Returns:
        pd.DataFrame: Cleaned DataFrame with duplicates removed.
    """
    cleaned = df.copy()

    # Drop rows where any required value is missing
    cleaned = cleaned.dropna(subset=OUTPUT_COLUMNS)

    if cleaned.empty:
        raise ValueError("No valid records remain after removing missing values.")

    # Avoid duplicate city + timestamp combinations
    cleaned = cleaned.drop_duplicates(subset=["city", "recorded_at"], keep="last")

    return cleaned.reset_index(drop=True)


def save_processed_csv(df: pd.DataFrame) -> Path:
    """
    Save transformed data as a timestamped CSV file.

    Args:
        df: Cleaned weather DataFrame.

    Returns:
        Path: Location where the CSV was saved.
    """
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"weather_processed_{timestamp}.csv"
    filepath = PROCESSED_DATA_DIR / filename

    df.to_csv(filepath, index=False)

    return filepath


def transform_weather(raw_filepath: Path | None = None) -> Path:
    """
    Main transformation function: raw JSON -> validated DataFrame -> CSV.

    Args:
        raw_filepath: Optional specific raw file to transform.
                      If omitted, the latest file in data/raw/ is used.

    Returns:
        Path: Path to the saved processed CSV file.
    """
    source_file = raw_filepath or find_latest_raw_file()
    print(f"Reading raw weather data from: {source_file}")

    raw_data = load_raw_json(source_file)
    record = extract_weather_fields(raw_data)
    validate_weather_record(record)

    df = build_dataframe(record)
    cleaned_df = clean_dataframe(df)

    output_path = save_processed_csv(cleaned_df)

    print(f"Transformation successful. Processed data saved to: {output_path}")
    print(cleaned_df.to_string(index=False))

    return output_path


def main() -> None:
    """Run transformation when this file is executed directly."""
    try:
        transform_weather()
    except FileNotFoundError as exc:
        print(f"Transformation failed — raw file not found: {exc}")
        raise SystemExit(1) from exc
    except ValueError as exc:
        print(f"Transformation failed — data validation error: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
