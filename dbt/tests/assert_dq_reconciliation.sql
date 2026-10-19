-- Every raw trip must be accounted for: raw rows = rows in fct_trips + rows rejected.
-- Returns a row (= test failure) if any trips were silently dropped or duplicated.
with raw_count as (
    select count(*) as n from {{ source('raw', 'yellow_trips_raw') }}
),
fct as (
    select count(*) as n from {{ ref('fct_trips') }}
),
rejected as (
    select count(*) as n from {{ ref('int_trips_dq_flagged') }} where is_valid = 0
)
select
    raw_count.n as raw_rows,
    fct.n       as fct_rows,
    rejected.n  as rejected_rows
from raw_count, fct, rejected
where raw_count.n <> fct.n + rejected.n
