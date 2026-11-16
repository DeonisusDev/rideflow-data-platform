{{ config(tags=['taxi']) }}
-- Reconciliation per source month, without rescanning staging:
--   raw rows == all DQ-labelled rows   (nothing lost or duplicated in staging)
--   'ok' rows == rows in fct_trips     (fct holds exactly the valid trips)
-- Only months fct_trips has processed are checked: a month (re)loaded into raw after the
-- last transform (newer _loaded_at, e.g. ingest running during a backfill) is pending.
with
watermark as (select max(_loaded_at) as w from {{ ref('fct_trips') }}),
raw_m as (
    select _source_month, count() as raw_rows, max(_loaded_at) as loaded_at
    from {{ source('raw', 'yellow_trips') }} group by _source_month
),
dq_m as (
    select source_month, sum(rows) as dq_rows, sumIf(rows, dq_status = 'ok') as ok_rows
    from {{ ref('dq_trip_rejections') }} group by source_month
),
fct_m as (
    select _source_month, count() as fct_rows
    from {{ ref('fct_trips') }} group by _source_month
)
select r._source_month, r.raw_rows, d.dq_rows, d.ok_rows, f.fct_rows
from raw_m r
left join dq_m d  on d.source_month  = r._source_month
left join fct_m f on f._source_month = r._source_month
where r.loaded_at <= (select w from watermark)
  and (r.raw_rows != d.dq_rows or d.ok_rows != f.fct_rows)
