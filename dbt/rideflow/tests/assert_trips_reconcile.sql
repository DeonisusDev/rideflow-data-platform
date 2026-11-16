{{ config(tags=['taxi']) }}
-- Reconciliation: per source month, valid rows in staging == rows in fct_trips.
-- Only months fct_trips has already processed are checked: a month (re)loaded into raw
-- after fct was built (newer _loaded_at — e.g. ingest running during a backfill)
-- is pending, not broken; the next taxi_transform run picks it up.
with fct_watermark as (
    select max(_loaded_at) as loaded_at from {{ ref('fct_trips') }}
),
s as (
    select _source_month, countIf(dq_status = 'ok') as expected
    from {{ ref('stg_yellow_trips') }}
    where _loaded_at <= (select loaded_at from fct_watermark)
    group by _source_month
),
f as (
    select _source_month, count() as actual
    from {{ ref('fct_trips') }} group by _source_month
)
select s._source_month, expected, f.actual
from s left join f on f._source_month = s._source_month
where expected != f.actual
