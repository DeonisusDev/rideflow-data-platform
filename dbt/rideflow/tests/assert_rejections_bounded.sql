{{ config(tags=['taxi'], severity='warn') }}
-- Alarm if a month rejects more than 10% of rows: likely a source format change.
select source_month, sum(pct) as rejected_pct
from {{ ref('dq_trip_rejections') }}
where dq_status != 'ok'
group by source_month
having rejected_pct > 10
