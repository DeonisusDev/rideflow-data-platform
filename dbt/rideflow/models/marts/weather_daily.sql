{{ config(tags=['weather']) }}
select
    day,
    count()                                   as hours_observed,
    round(min(temperature_c), 1)              as temp_min_c,
    round(max(temperature_c), 1)              as temp_max_c,
    round(avg(temperature_c), 1)              as temp_avg_c,
    round(sum(precipitation_mm), 1)           as precipitation_mm,
    round(sum(snowfall_cm), 1)                as snowfall_cm,
    countIf(is_wet)                           as wet_hours,
    topK(1)(condition)[1]                     as dominant_condition
from {{ ref('dim_weather_hour') }}
group by day
