{{ config(tags=['taxi']) }}
-- Weather vs demand: one row per hour with trip KPIs and that hour's weather.
with demand as (
    select
        pickup_hour                         as hour_ts,
        count()                             as trips,
        round(sum(total_amount), 2)         as revenue,
        round(avg(fare_amount), 2)          as avg_fare,
        round(avg(duration_min), 1)         as avg_duration_min,
        round(avg(avg_speed_mph), 1)        as avg_speed_mph,
        round(avg(tip_rate), 3)             as avg_tip_rate
    from {{ ref('fct_trips') }}
    group by pickup_hour
)
select
    d.*,
    toDate(d.hour_ts)                       as day,            -- local NYC date (browser DuckDB has no tz support)
    toHour(d.hour_ts)                       as hour_of_day,
    toDayOfWeek(d.hour_ts)                  as day_of_week,    -- 1 = Monday
    w.temperature_c,
    w.precipitation_mm,
    w.snowfall_cm,
    w.condition,
    w.is_wet
from demand d
left join {{ ref('dim_weather_hour') }} w on w.hour_ts = d.hour_ts
