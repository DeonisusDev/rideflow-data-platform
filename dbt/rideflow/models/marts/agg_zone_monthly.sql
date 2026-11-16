{{ config(tags=['taxi']) }}
select
    toStartOfMonth(f.pickup_date)           as month,
    z.zone_id,
    z.borough,
    z.zone,
    count()                                 as pickups,
    round(sum(f.total_amount), 2)           as revenue,
    round(avg(f.trip_distance_mi), 2)       as avg_distance_mi,
    round(avg(f.tip_rate), 3)               as avg_tip_rate
from {{ ref('fct_trips') }} f
join {{ ref('dim_zone') }} z on z.zone_id = f.pickup_zone_id
group by month, z.zone_id, z.borough, z.zone
