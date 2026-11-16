{{ config(
    tags=['taxi'],
    materialized='incremental',
    incremental_strategy='insert_overwrite',
    partition_by='_source_month',
    order_by='(pickup_zone_id, pickup_ts)',
    engine='MergeTree()'
) }}
-- Grain: one valid trip. Re-loading a month in raw (new _loaded_at) overwrites
-- exactly that partition here — idempotent backfills.
select
    pickup_ts,
    dropoff_ts,
    toStartOfHour(pickup_ts)                 as pickup_hour,
    toDate(pickup_ts)                        as pickup_date,
    toUInt16(assumeNotNull(pu_location_id))  as pickup_zone_id,   -- null zones rejected in staging
    toUInt16(assumeNotNull(do_location_id))  as dropoff_zone_id,
    vendor_id,
    passenger_count,
    trip_distance_mi,
    round(duration_min, 2)                   as duration_min,
    round(avg_speed_mph, 2)                  as avg_speed_mph,
    transform(payment_type, [1, 2, 3, 4], ['card', 'cash', 'no_charge', 'dispute'], 'other') as payment_method,
    fare_amount,
    tip_amount,
    tolls_amount,
    total_amount,
    if(payment_type = 1, tip_amount / fare_amount, null) as tip_rate,   -- cash tips are not recorded
    _source_month,
    _loaded_at
from {{ ref('stg_yellow_trips') }}
where dq_status = 'ok'
{% if is_incremental() %}
  and _loaded_at > (select max(_loaded_at) from {{ this }})
{% endif %}
