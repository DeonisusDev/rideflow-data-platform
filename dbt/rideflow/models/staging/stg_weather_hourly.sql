{{ config(tags=['weather']) }}
-- One row per (location, hour). FINAL collapses re-ingested duplicates.
select
    location,
    ts                                   as hour_ts,
    toDate(ts)                           as day,      -- local NYC date (column tz)
    temperature_c,
    coalesce(precipitation_mm, 0)        as precipitation_mm,
    coalesce(rain_mm, 0)                 as rain_mm,
    coalesce(snowfall_cm, 0)             as snowfall_cm,
    wind_speed_kmh,
    weather_code,
    _ingested_at
from {{ source('raw', 'weather_hourly') }} final
-- Archive API returns the newest ~5 days as NULLs (not measured yet).
-- Drop them here; the trailing re-ingest window fills them on later runs.
where temperature_c is not null
