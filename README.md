# Weather ETL Pipeline

![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?logo=pandas&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)

An end-to-end Data Engineering project that extracts real-time weather data from the Open-Meteo API, transforms and validates it using Python and Pandas, and loads it into PostgreSQL for SQL-based analysis.

---

## Project Overview

The **Weather ETL Pipeline** is designed to demonstrate core Data Engineering principles by building a robust, production-style Data Pipeline. The pipeline extracts current weather observations for Pune, India from the Open-Meteo REST API, cleans and validates the data using Pandas, and loads it into a PostgreSQL relational database table with built-in duplicate prevention.

### Key Concepts Demonstrated
- **ETL Design**: Clear separation of Extract, Transform, and Load operations.
- **API Data Ingestion**: Programmatic data retrieval using HTTP Requests.
- **Data Validation & Transformation**: Schema validation, data type enforcement, and null checks using Pandas.
- **Relational Storage**: PostgreSQL schema design with constraints, indexes, and primary keys.
- **Idempotent Pipeline**: Duplicate protection using `(city, recorded_at)` unique constraint and `ON CONFLICT DO NOTHING`.
- **Pipeline Orchestration**: Centralized coordination with fail-fast execution and execution timing.
- **Security Best Practices**: Decoupled environment credentials via `.env`.

---

## Architecture

```
Open-Meteo API
      │
      ▼
   extract.py
      │
      ▼
Raw JSON Files ────► (data/raw/)
      │
      ▼
  transform.py
      │
      ▼
Pandas DataFrame
      │
      ▼
Processed CSV ─────► (data/processed/)
      │
      ▼
    load.py
      │
      ▼
 PostgreSQL ──────► (weather_db -> weather table)
      │
      ▼
  SQL Analysis ────► (sql/analysis.sql)
```

The orchestrator script (`src/pipeline.py`) coordinates `extract.py` ➔ `transform.py` ➔ `load.py` in sequence.

---

## ETL Workflow

### 1. Extract (`src/extract.py`)
- Calls the free Open-Meteo REST API endpoint for Pune weather (Latitude: 18.52, Longitude: 73.86).
- Fetches real-time weather metrics: `temperature_2m`, `relative_humidity_2m`, and `wind_speed_10m`.
- Saves the complete raw JSON response into `data/raw/` with a timestamped filename (e.g., `weather_20260724_140000.json`).
- **Purpose**: Preserves raw source data for auditability and reproducible reprocessing.

### 2. Transform (`src/transform.py`)
- Reads the raw JSON file generated in the Extract step.
- Extracts and maps nested API attributes into a structured dataset.
- Performs runtime data validation:
  - Verifies presence of all required fields.
  - Ensures humidity stays within valid bounds (0% to 100%).
- Constructs a Pandas DataFrame, enforces column data types, and drops potential duplicates.
- Writes the cleaned dataset to `data/processed/` as a timestamped CSV file (e.g., `weather_processed_20260724_140000.csv`).

### 3. Load (`src/load.py`)
- Parses environment credentials securely from `.env` using `python-dotenv`.
- Establishes a connection to the PostgreSQL database (`weather_db`) via `psycopg2`.
- Inserts weather records into the `weather` table.
- Employs `ON CONFLICT (city, recorded_at) DO NOTHING` to ensure idempotency and prevent duplicate records.

### 4. Orchestration (`src/pipeline.py`)
- Runs the entire ETL workflow using a single command: `python src/pipeline.py`.
- Enforces strict sequential order: Extract ➔ Transform ➔ Load.
- Incorporates fail-fast error handling: stops execution immediately if any stage fails and returns a non-zero exit code.
- Measures total pipeline execution duration.

---

## Tech Stack

| Technology | Category | Role in Project |
| :--- | :--- | :--- |
| **Python 3** | Language | Primary programming language for the ETL pipeline |
| **Requests** | Library | Communicates with Open-Meteo REST API |
| **Pandas** | Library | Data cleaning, type conversion, and DataFrame manipulation |
| **PostgreSQL** | Database | Relational database management system storing processed data |
| **psycopg2** | Database Driver | Connects Python scripts to PostgreSQL |
| **python-dotenv** | Security | Loads configuration & secrets from `.env` files |
| **SQL** | Query Language | Schema creation and data analysis |
| **Git / GitHub** | Version Control | Source code control and project documentation |

---

## Project Structure

```text
weather-etl-pipeline/
├── data/
│   ├── raw/
│   │   └── .gitkeep
│   └── processed/
│       └── .gitkeep
├── sql/
│   ├── create_table.sql
│   └── analysis.sql
├── src/
│   ├── extract.py
│   ├── transform.py
│   ├── load.py
│   └── pipeline.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Database Schema

Database: `weather_db`  
Table: `weather`

```sql
CREATE TABLE IF NOT EXISTS weather (
    id SERIAL PRIMARY KEY,
    city VARCHAR(100) NOT NULL,
    temperature_c NUMERIC(5, 2) NOT NULL,
    humidity_percent NUMERIC(5, 2) NOT NULL,
    wind_speed_kmh NUMERIC(6, 2) NOT NULL,
    recorded_at TIMESTAMP NOT NULL,
    loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_weather_city_recorded_at UNIQUE (city, recorded_at),
    CONSTRAINT chk_humidity_range CHECK (humidity_percent >= 0 AND humidity_percent <= 100)
);
```

### Column Descriptions & Constraints
- `id`: Auto-incrementing primary key.
- `city`: Name of the city (e.g., "Pune").
- `temperature_c`: Temperature reading in degrees Celsius.
- `humidity_percent`: Relative humidity (enforced `0-100%` via `CHECK` constraint).
- `wind_speed_kmh`: Wind speed in kilometers per hour.
- `recorded_at`: **Event Time** — timestamp when observation was recorded by Open-Meteo.
- `loaded_at`: **Ingestion Time** — timestamp when record was inserted into PostgreSQL (`DEFAULT CURRENT_TIMESTAMP`).
- `uq_weather_city_recorded_at`: **UNIQUE Constraint** — prevents duplicate observations for the same city at the same recorded time.

---

## SQL Analysis

The repository includes [`sql/analysis.sql`](sql/analysis.sql) containing analytical queries to extract insights from stored weather records.

### Concepts Covered
- Aggregate Functions (`COUNT`, `AVG`, `MIN`, `MAX`, `ROUND`)
- Grouping & Filtering (`GROUP BY`, `WHERE`, `ORDER BY DESC`)
- Date Extraction (`DATE(recorded_at)`)
- Window Functions (`LAG() OVER (PARTITION BY ... ORDER BY ...)`)

### Key Business Questions Answered
1. What is the latest weather reading?
2. What are the daily average, minimum, and maximum temperatures?
3. Which record recorded the peak wind speed?
4. What is the average ingestion latency (`loaded_at - recorded_at`)?
5. How much did temperature shift between consecutive observations?

---

## Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/Aman6124/weather-etl-pipeline.git
cd weather-etl-pipeline
```

### 2. Create and Activate Virtual Environment

**Windows (CMD):**
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
python -m pip install -r requirements.txt
```

### 4. PostgreSQL Database Setup
Ensure PostgreSQL is running locally, then open your terminal or `psql` shell:

```sql
CREATE DATABASE weather_db;
```

Run the table creation script:
```bash
psql -U postgres -d weather_db -f sql/create_table.sql
```

### 5. Environment Configuration
Copy `.env.example` to create your local `.env` file:
**Windows (CMD or PowerShell):**
```text
copy .env.example .env
```

**macOS / Linux:**
```bash
cp .env.example .env
```

Edit `.env` with your local PostgreSQL password and settings:
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=weather_db
DB_USER=postgres
DB_PASSWORD=your_actual_password
```

> ⚠️ **Warning**: Never commit your `.env` file to version control. It is listed in `.gitignore`.

---

## Running the Pipeline & Analysis

### Execute End-to-End ETL Pipeline
Run the complete pipeline with a single command:
```bash
python src/pipeline.py
```

### Run SQL Data Analysis
Execute analytical queries against your populated database:
```bash
psql -U postgres -d weather_db -f sql/analysis.sql
```

---

## Example Pipeline Output

```text
========================================
WEATHER ETL PIPELINE
====================

[1/3] EXTRACT
Fetching weather data for Pune from Open-Meteo API...
Extraction successful. Raw data saved to: data/raw/weather_20260724_140000.json

[2/3] TRANSFORM
Reading raw weather data from: data/raw/weather_20260724_140000.json
Transformation successful. Processed data saved to: data/processed/weather_processed_20260724_140000.csv
city  temperature_c  humidity_percent  wind_speed_kmh         recorded_at
Pune           26.2              78.0            27.4 2026-07-24 14:00:00

[3/3] LOAD
Starting Load step...
Connecting to PostgreSQL...
Connected to PostgreSQL successfully.
Loading weather records...

Inserted: 1
Duplicates skipped: 0

Load completed successfully.

========================================
ETL PIPELINE COMPLETED SUCCESSFULLY
===================================
Pipeline execution time: 1.27 seconds
```

---

## Data Engineering Concepts Demonstrated

- **Modular ETL Design**: Decoupled extract, transform, and load stages for modular testing and maintenance.
- **Data Preservation**: Preserving immutable raw JSON snapshots prior to transformation.
- **Idempotency**: Using PostgreSQL `UNIQUE` constraints and `ON CONFLICT` clauses to prevent duplicate rows across pipeline re-runs.
- **Data Quality & Validation**: In-line validation checking for missing values and value range bounds.
- **Event vs. Ingestion Time**: Distinguishing observation time (`recorded_at`) from loading time (`loaded_at`).
- **Fail-Fast Error Handling**: Immediate execution termination with clear diagnostics upon failure.

---

## Future Improvements

- **Pipeline Scheduling**: Automate periodic pipeline runs using `cron` or Task Scheduler.
- **Workflow Management**: Migrate pipeline orchestration to Apache Airflow or Prefect.
- **Containerization**: Package application environment using Docker & Docker Compose.
- **Multi-City Support**: Scale extraction to ingest weather data for multiple global cities.
- **Cloud Storage**: Store raw JSON and processed CSV files in AWS S3 or Google Cloud Storage.
- **Unit Testing**: Implement pytest suites for automated code verification.
- **Dashboarding**: Connect PostgreSQL to Grafana or Metabase for interactive visualization.

---

## Author

**Aman Patwegar**  
Data Engineer | Data Analyst  
