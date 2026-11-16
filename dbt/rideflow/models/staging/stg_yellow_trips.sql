{{ config(tags=['taxi']) }}
-- Every source row survives here with a dq_status; fct keeps only 'ok'.
-- dq_trip_rejections reports the rest, so nothing disappears silently.
with typed as (
    select
        -- naive local wall clock → real instant in NYC tz
        toDateTime(toString(toDateTime(pickup_local)),  'America/New_York') as pickup_ts,
        toDateTime(toString(toDateTime(dropoff_local)), 'America/New_York') as dropoff_ts,
        vendor_id,
        toUInt8OrNull(toString(passenger_count))   as passenger_count,
        trip_distance                              as trip_distance_mi,
        pu_location_id,
        do_location_id,
        payment_type,
        fare_amount,
        tip_amount,
        tolls_amount,
        total_amount,
        _source_month,
        _loaded_at
    from {{ source('raw', 'yellow_trips') }}
),
measured as (
    select
        *,
        dateDiff('second', pickup_ts, dropoff_ts) / 60.0 as duration_min,
        if(duration_min > 0, trip_distance_mi / (duration_min / 60.0), null) as avg_speed_mph
    from typed
)
select
    *,
    multiIf(
        pu_location_id is null or do_location_id is null, 'missing_zone',
        toYYYYMM(pickup_ts) != _source_month,         'out_of_month',
        duration_min <= 0,                            'non_positive_duration',
        duration_min > 360,                           'duration_over_6h',
        trip_distance_mi <= 0,                        'zero_distance',
        trip_distance_mi > 200,                       'distance_outlier',
        fare_amount <= 0 or total_amount <= 0,        'non_positive_amount',
        avg_speed_mph > 80,                           'speed_outlier',
        pu_location_id in (264, 265) or do_location_id in (264, 265), 'unknown_zone',
        'ok'
    ) as dq_status
from measured
