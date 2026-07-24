-- =============================================================================
-- Weather ETL Pipeline — SQL Data Analysis Queries
-- =============================================================================
-- This script contains analytical queries designed to inspect and analyze the
-- weather records loaded in PostgreSQL (weather_db -> weather table).
--
-- Execution:
--   psql -U postgres -d weather_db -f sql/analysis.sql
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. VIEW ALL DATA
-- Description: Retrieves all weather observations, newest first.
-- Concept: SELECT *, ORDER BY ... DESC
-- -----------------------------------------------------------------------------
SELECT 
    id,
    city,
    temperature_c,
    humidity_percent,
    wind_speed_kmh,
    recorded_at,
    loaded_at
FROM weather
ORDER BY recorded_at DESC;


-- -----------------------------------------------------------------------------
-- 2. TOTAL RECORD COUNT
-- Description: Counts the total number of weather observations in the table.
-- Concept: Aggregate function COUNT()
-- -----------------------------------------------------------------------------
SELECT 
    COUNT(*) AS total_records
FROM weather;


-- -----------------------------------------------------------------------------
-- 3. LATEST WEATHER READING
-- Description: Fetches the single most recent weather observation recorded.
-- Concept: ORDER BY recorded_at DESC with LIMIT 1
-- -----------------------------------------------------------------------------
SELECT 
    *
FROM weather
ORDER BY recorded_at DESC
LIMIT 1;


-- -----------------------------------------------------------------------------
-- 4. AVERAGE TEMPERATURE
-- Description: Calculates the overall average temperature rounded to 2 decimal places.
-- Concept: AVG() aggregate function combined with ROUND()
-- -----------------------------------------------------------------------------
SELECT 
    ROUND(AVG(temperature_c), 2) AS avg_temperature_c
FROM weather;


-- -----------------------------------------------------------------------------
-- 5. MINIMUM AND MAXIMUM TEMPERATURE
-- Description: Retrieves the lowest and highest temperatures recorded.
-- Concept: MIN() and MAX() aggregate functions
-- -----------------------------------------------------------------------------
SELECT 
    MIN(temperature_c) AS min_temperature_c,
    MAX(temperature_c) AS max_temperature_c
FROM weather;


-- -----------------------------------------------------------------------------
-- 6. AVERAGE HUMIDITY
-- Description: Calculates the average relative humidity percentage across all readings.
-- Concept: AVG() and ROUND()
-- -----------------------------------------------------------------------------
SELECT 
    ROUND(AVG(humidity_percent), 2) AS avg_humidity_percent
FROM weather;


-- -----------------------------------------------------------------------------
-- 7. AVERAGE WIND SPEED
-- Description: Calculates the average wind speed in kilometers per hour.
-- Concept: AVG() and ROUND()
-- -----------------------------------------------------------------------------
SELECT 
    ROUND(AVG(wind_speed_kmh), 2) AS avg_wind_speed_kmh
FROM weather;


-- -----------------------------------------------------------------------------
-- 8. DAILY WEATHER SUMMARY
-- Description: Summarizes daily weather metrics (reading count, averages, min/max).
-- Concept: DATE() function, GROUP BY date, multiple aggregate functions
-- -----------------------------------------------------------------------------
SELECT 
    DATE(recorded_at) AS reading_date,
    COUNT(*) AS total_readings,
    ROUND(AVG(temperature_c), 2) AS avg_temperature_c,
    MIN(temperature_c) AS min_temperature_c,
    MAX(temperature_c) AS max_temperature_c,
    ROUND(AVG(humidity_percent), 2) AS avg_humidity_percent,
    ROUND(AVG(wind_speed_kmh), 2) AS avg_wind_speed_kmh
FROM weather
GROUP BY DATE(recorded_at)
ORDER BY reading_date DESC;


-- -----------------------------------------------------------------------------
-- 9. TEMPERATURE BY CITY
-- Description: Groups metrics by city name to prepare for multi-city data growth.
-- Concept: GROUP BY categorical column
-- -----------------------------------------------------------------------------
SELECT 
    city,
    COUNT(*) AS total_readings,
    ROUND(AVG(temperature_c), 2) AS avg_temperature_c,
    MIN(temperature_c) AS min_temperature_c,
    MAX(temperature_c) AS max_temperature_c
FROM weather
GROUP BY city;


-- -----------------------------------------------------------------------------
-- 10. HIGHEST TEMPERATURE READING
-- Description: Finds the complete row corresponding to the highest temperature.
-- Concept: Filtering extreme record using ORDER BY column DESC and LIMIT 1
-- -----------------------------------------------------------------------------
SELECT 
    *
FROM weather
ORDER BY temperature_c DESC
LIMIT 1;


-- -----------------------------------------------------------------------------
-- 11. HIGHEST WIND SPEED READING
-- Description: Finds the complete row corresponding to the peak wind speed.
-- Concept: ORDER BY numeric column DESC with LIMIT 1
-- -----------------------------------------------------------------------------
SELECT 
    *
FROM weather
ORDER BY wind_speed_kmh DESC
LIMIT 1;


-- -----------------------------------------------------------------------------
-- 12. HUMID WEATHER READINGS
-- Description: Filters records where relative humidity is 80% or higher.
-- Concept: Conditional filtering using WHERE clause with comparison operator (>=)
-- -----------------------------------------------------------------------------
SELECT 
    *
FROM weather
WHERE humidity_percent >= 80.0
ORDER BY recorded_at DESC;


-- -----------------------------------------------------------------------------
-- 13. DATA LOADING INFORMATION
-- Description: Compares event time (recorded_at) against ingestion time (loaded_at).
-- Concept: Timestamp arithmetic to calculate pipeline latency / ingestion delay
-- -----------------------------------------------------------------------------
SELECT 
    id,
    city,
    recorded_at,
    loaded_at,
    (loaded_at - recorded_at) AS ingestion_delay
FROM weather
ORDER BY recorded_at DESC;


-- -----------------------------------------------------------------------------
-- 14. READINGS PER DAY
-- Description: Counts total observations gathered per calendar day.
-- Concept: DATE() expression grouping and COUNT(*) aggregation
-- -----------------------------------------------------------------------------
SELECT 
    DATE(recorded_at) AS reading_date,
    COUNT(*) AS total_readings
FROM weather
GROUP BY DATE(recorded_at)
ORDER BY reading_date DESC;


-- -----------------------------------------------------------------------------
-- 15. TEMPERATURE CHANGE OVER TIME (WINDOW FUNCTION)
-- Description: Calculates temperature change between consecutive weather readings.
-- Concept: LAG() window function accesses data from the preceding row within a
--          partition without needing a self-join.
-- -----------------------------------------------------------------------------
SELECT 
    id,
    city,
    recorded_at,
    temperature_c,
    LAG(temperature_c) OVER (
        PARTITION BY city 
        ORDER BY recorded_at
    ) AS previous_temperature_c,
    ROUND(
        temperature_c - LAG(temperature_c) OVER (
            PARTITION BY city 
            ORDER BY recorded_at
        ), 
        2
    ) AS temp_change_c
FROM weather
ORDER BY recorded_at DESC;
