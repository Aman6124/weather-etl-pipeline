-- =============================================================================
-- Weather ETL Pipeline — Database Schema
-- =============================================================================
-- Run this script once to create the weather table in PostgreSQL.
--
-- Example (psql):
--   psql -U postgres -d weather_db -f sql/create_table.sql
-- =============================================================================

CREATE TABLE IF NOT EXISTS weather (
    -- Auto-incrementing primary key: unique identifier for every row
    id SERIAL PRIMARY KEY,

    -- City name (e.g. "Pune")
    city VARCHAR(100) NOT NULL,

    -- Temperature in degrees Celsius (supports values like -10.50 to 999.99)
    temperature_c NUMERIC(5, 2) NOT NULL,

    -- Relative humidity as a percentage (0–100)
    humidity_percent NUMERIC(5, 2) NOT NULL,

    -- Wind speed in km/h
    wind_speed_kmh NUMERIC(6, 2) NOT NULL,

    -- When the weather reading was recorded (from the API)
    recorded_at TIMESTAMP NOT NULL,

    -- When this row was loaded into the database (set automatically on insert)
    loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Prevent duplicate readings for the same city at the same time
    CONSTRAINT uq_weather_city_recorded_at UNIQUE (city, recorded_at),

    -- Database-level validation: humidity must stay within a valid range
    CONSTRAINT chk_humidity_range CHECK (
        humidity_percent >= 0 AND humidity_percent <= 100
    )
);

-- Optional: index to speed up queries filtered by city or date
CREATE INDEX IF NOT EXISTS idx_weather_city_recorded_at
    ON weather (city, recorded_at DESC);
