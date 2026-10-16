"""
Load module — inserts processed weather CSV data into PostgreSQL.

This is the "L" (Load) step of the ETL pipeline.
We read the latest cleaned CSV, connect to the database using credentials
from .env, and insert rows into the weather table with duplicate protection.
"""

import os
from pathlib import Path

import pandas as pd
import psycopg2
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Columns expected in the processed CSV and in the weather table
REQUIRED_COLUMNS = [
    "city",
    "temperature_c",
    "humidity_percent",
    "wind_speed_kmh",
    "recorded_at",
]

# Environment variables needed to connect to PostgreSQL
DB_ENV_VARS = ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"]

# Project paths (src/ is one level below project root)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
ENV_FILE = PROJECT_ROOT / ".env"


def find_latest_processed_file() -> Path:
    """
    Find the most recently modified processed weather CSV in data/processed/.

    Sorting by modification time ensures we always load the newest transform output.

    Returns:
        Path: Path to the latest processed CSV file.

    Raises:
        FileNotFoundError: If no processed CSV files exist.
    """
    processed_files = list(PROCESSED_DATA_DIR.glob("weather_processed_*.csv"))

    if not processed_files:
        raise FileNotFoundError(
            f"No processed weather CSV files found in {PROCESSED_DATA_DIR}. "
            "Run 'python src/transform.py' first."
        )

    return max(processed_files, key=lambda path: path.stat().st_mtime)


def load_processed_csv(filepath: Path) -> pd.DataFrame:
    """
    Read a processed CSV into a Pandas DataFrame and validate its schema.

    Schema validation before insert prevents confusing database errors later.

    Args:
        filepath: Path to the processed CSV file.

    Returns:
        pd.DataFrame: Weather records ready for loading.

    Raises:
        ValueError: If required columns are missing.
    """
    df = pd.read_csv(filepath, parse_dates=["recorded_at"])

    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_columns:
        raise ValueError(
            "Processed CSV is missing required columns: "
            f"{', '.join(missing_columns)}"
        )

    return df[REQUIRED_COLUMNS]


def get_database_config() -> dict:
    """
    Load PostgreSQL connection settings from the .env file.

    Keeping secrets in .env (not in source code) is a standard practice:
    credentials stay out of Git and can differ per environment (local vs cloud).

    Returns:
        dict: Database connection parameters.

    Raises:
        ValueError: If any required environment variable is missing or empty.
    """
    load_dotenv(ENV_FILE)

    config = {}
    missing_vars = []

    for var_name in DB_ENV_VARS:
        value = os.getenv(var_name)
        # Password whitespace is part of the credential, not formatting.
        if value is not None and var_name != "DB_PASSWORD":
            value = value.strip()
        if value is None or value == "":
            missing_vars.append(var_name)
        else:
            config[var_name.lower()] = value

    if missing_vars:
        raise ValueError(
            "Missing required database environment variables in .env: "
            f"{', '.join(missing_vars)}"
        )

    return {
        "host": config["db_host"],
        "port": config["db_port"],
        "dbname": config["db_name"],
        "user": config["db_user"],
        "password": config["db_password"],
    }


def connect_to_database(config: dict):
    """
    Open a connection to PostgreSQL using psycopg2.

    psycopg2 is a Python driver that speaks PostgreSQL's wire protocol,
    letting our script send SQL commands to the database server.

    Args:
        config: Connection parameters from get_database_config().

    Returns:
        psycopg2 connection object.
    """
    connection = psycopg2.connect(**config)
    print("Connected to PostgreSQL successfully.")
    return connection


def insert_weather_records(connection, df: pd.DataFrame) -> tuple[int, int]:
    """
    Insert weather rows into the weather table, skipping duplicates.

    ON CONFLICT DO NOTHING relies on the UNIQUE (city, recorded_at) constraint
    already defined in sql/create_table.sql.

    Args:
        connection: Active PostgreSQL connection.
        df: DataFrame of weather records to insert.

    Returns:
        tuple[int, int]: Count of (inserted rows, duplicate rows skipped).
    """
    insert_sql = """
        INSERT INTO weather (
            city,
            temperature_c,
            humidity_percent,
            wind_speed_kmh,
            recorded_at
        )
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (city, recorded_at) DO NOTHING
        RETURNING id
    """

    inserted_count = 0
    skipped_count = 0

    cursor = connection.cursor()

    try:
        for row in df.itertuples(index=False):
            # Convert Pandas Timestamp to native Python datetime for psycopg2
            recorded_at = row.recorded_at
            if hasattr(recorded_at, "to_pydatetime"):
                recorded_at = recorded_at.to_pydatetime()

            cursor.execute(
                insert_sql,
                (
                    row.city,
                    float(row.temperature_c),
                    float(row.humidity_percent),
                    float(row.wind_speed_kmh),
                    recorded_at,
                ),
            )

            # RETURNING id is populated only when a new row is inserted
            if cursor.fetchone():
                inserted_count += 1
            else:
                skipped_count += 1
    finally:
        cursor.close()

    return inserted_count, skipped_count


def load_weather(processed_filepath: Path | None = None) -> tuple[int, int]:
    """
    Main load function: read processed CSV and insert records into PostgreSQL.

    Args:
        processed_filepath: Optional specific CSV to load.
                            If omitted, the latest file in data/processed/ is used.

    Returns:
        tuple[int, int]: Count of (inserted rows, duplicate rows skipped).
    """
    print("Starting Load step...\n")

    source_file = processed_filepath or find_latest_processed_file()

    print("Reading processed data:")
    print(source_file)
    print()

    df = load_processed_csv(source_file)
    record_count = len(df)
    record_label = "record" if record_count == 1 else "records"
    print(f"{record_count} {record_label} ready for loading.\n")

    db_config = get_database_config()

    print("Connecting to PostgreSQL...")
    connection = connect_to_database(db_config)
    print()

    try:
        print("Loading weather records...\n")
        inserted_count, skipped_count = insert_weather_records(connection, df)
        connection.commit()

        print(f"Inserted: {inserted_count}")
        print(f"Duplicates skipped: {skipped_count}\n")
        print("Load completed successfully.")

        return inserted_count, skipped_count
    except Exception:
        # Rollback undoes any partial inserts if something fails mid-load
        connection.rollback()
        raise
    finally:
        connection.close()


def main() -> None:
    """Run the load step when this file is executed directly."""
    try:
        load_weather()
    except FileNotFoundError as exc:
        print(f"Load failed — processed file not found: {exc}")
        raise SystemExit(1) from exc
    except ValueError as exc:
        print(f"Load failed — configuration or data error: {exc}")
        raise SystemExit(1) from exc
    except psycopg2.Error as exc:
        print(f"Load failed — database error: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
