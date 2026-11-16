{{ config(tags=['taxi']) }}
-- Every demand hour must find its weather hour (else the weather pipeline is behind).
select hour_ts from {{ ref('agg_demand_hourly') }} where condition = ''
