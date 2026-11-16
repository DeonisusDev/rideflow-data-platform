{{ config(tags=['taxi']) }}
select
    _source_month                                                   as source_month,
    dq_status,
    count()                                                         as rows,
    round(100 * count() / sum(count()) over (partition by _source_month), 3) as pct
from {{ ref('stg_yellow_trips') }}
group by _source_month, dq_status
