{{ config(tags=['weather']) }}
-- Physically implausible NYC readings mean a broken source or unit change.
select *
from {{ ref('dim_weather_hour') }}
where temperature_c not between -35 and 45
   or precipitation_mm not between 0 and 150
   or wind_speed_kmh not between 0 and 200
