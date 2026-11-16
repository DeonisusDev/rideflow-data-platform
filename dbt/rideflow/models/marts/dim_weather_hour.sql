{{ config(tags=['weather']) }}
-- Hourly weather dimension: joined to trips by hour (stage 1, NYC TLC).
-- WMO weather codes → coarse conditions: https://open-meteo.com/en/docs
select
    hour_ts,
    day,
    temperature_c,
    precipitation_mm,
    snowfall_cm,
    wind_speed_kmh,
    weather_code,
    multiIf(
        weather_code in (71, 73, 75, 77, 85, 86), 'snow',
        weather_code in (95, 96, 99),             'storm',
        weather_code >= 51,                       'rain',
        weather_code in (45, 48),                 'fog',
        weather_code in (1, 2, 3),                'cloudy',
        'clear'
    )                                             as condition,
    precipitation_mm > 0.1 or snowfall_cm > 0     as is_wet
from {{ ref('stg_weather_hourly') }}
where location = 'nyc'
