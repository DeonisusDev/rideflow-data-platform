{{ config(
    tags=['taxi'],
    materialized='incremental',
    incremental_strategy='insert_overwrite',
    partition_by='toYYYYMM(month)',
    order_by='(month, zone_id)',
    engine='MergeTree()'
) }}
-- Aggregate 100M+ trips first, then join the 265-row zone dimension (not the other way round).
-- Incremental: only months whose fct partition changed are recomputed.
with by_zone as (
    select
        toStartOfMonth(pickup_date)          as month,
        pickup_zone_id                       as zone_id,
        count()                              as pickups,
        round(sum(total_amount), 2)          as revenue,
        round(avg(trip_distance_mi), 2)      as avg_distance_mi,
        round(avg(tip_rate), 3)              as avg_tip_rate,
        max(_loaded_at)                      as last_loaded_at  -- not _loaded_at: alias would shadow the column in WHERE
    from {{ ref('fct_trips') }}
    {% if is_incremental() %}
    where _loaded_at > (select max(last_loaded_at) from {{ this }})
    {% endif %}
    group by month, zone_id
)
select
    b.month, b.zone_id, z.borough, z.zone,
    b.pickups, b.revenue, b.avg_distance_mi, b.avg_tip_rate, b.last_loaded_at
from by_zone b
join {{ ref('dim_zone') }} z on z.zone_id = b.zone_id
