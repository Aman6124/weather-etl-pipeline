"""
ETL Pipeline Orchestrator — coordinates Extract, Transform, and Load steps.

This module acts as the central control for the Weather ETL Pipeline.
It executes extract.py -> transform.py -> load.py in sequence, timing execution
and stopping immediately if any stage encounters an error.
"""

import sys
import time
from pathlib import Path

# Ensure src/ directory is in the Python module search path
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Import existing ETL stage functions
from extract import extract_weather
from transform import transform_weather
from load import load_weather


def run_pipeline() -> None:
    """
    Orchestrate the complete ETL pipeline execution in sequence.

    1. Extract weather data from Open-Meteo API -> raw JSON file
    2. Transform raw JSON file -> cleaned CSV file
    3. Load cleaned CSV file -> PostgreSQL database
    """
    print("=" * 40)
    print("WEATHER ETL PIPELINE")
    print("=" * 20)
    print()

    start_time = time.time()

    # -----------------------------------------------------------------------
    # Stage 1: Extract
    # -----------------------------------------------------------------------
    print("[1/3] EXTRACT")
    try:
        raw_filepath = extract_weather()
    except Exception as exc:
        print(f"\n[ERROR] Pipeline failed at EXTRACT stage: {exc}")
        sys.exit(1)

    print()

    # -----------------------------------------------------------------------
    # Stage 2: Transform
    # -----------------------------------------------------------------------
    print("[2/3] TRANSFORM")
    try:
        processed_filepath = transform_weather(raw_filepath)
    except Exception as exc:
        print(f"\n[ERROR] Pipeline failed at TRANSFORM stage: {exc}")
        sys.exit(1)

    print()

    # -----------------------------------------------------------------------
    # Stage 3: Load
    # -----------------------------------------------------------------------
    print("[3/3] LOAD")
    try:
        load_weather(processed_filepath)
    except Exception as exc:
        print(f"\n[ERROR] Pipeline failed at LOAD stage: {exc}")
        sys.exit(1)

    # Calculate execution duration
    elapsed_time = time.time() - start_time

    print()
    print("=" * 40)
    print("ETL PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 35)
    print(f"Pipeline execution time: {elapsed_time:.2f} seconds")


def main() -> None:
    """Main entry point for pipeline execution."""
    run_pipeline()


if __name__ == "__main__":
    main()
