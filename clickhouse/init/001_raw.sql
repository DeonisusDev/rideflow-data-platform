-- Raw layer: data lands as-is from sources. dbt builds staging/marts on top.
CREATE DATABASE IF NOT EXISTS raw;

-- Hourly weather for NYC from Open-Meteo archive API.
-- ReplacingMergeTree makes re-ingestion idempotent: the latest _ingested_at wins.
CREATE TABLE IF NOT EXISTS raw.weather_hourly
(
    location        LowCardinality(String),
    latitude        Float32,
    longitude       Float32,
    ts              DateTime('America/New_York'),
    temperature_c   Nullable(Float32),
    precipitation_mm Nullable(Float32),
    rain_mm         Nullable(Float32),
    snowfall_cm     Nullable(Float32),
    wind_speed_kmh  Nullable(Float32),
    weather_code    Nullable(UInt8),
    _source         LowCardinality(String),
    _ingested_at    DateTime64(3, 'UTC')
)
ENGINE = ReplacingMergeTree(_ingested_at)
PARTITION BY toYYYYMM(ts)
ORDER BY (location, ts);
