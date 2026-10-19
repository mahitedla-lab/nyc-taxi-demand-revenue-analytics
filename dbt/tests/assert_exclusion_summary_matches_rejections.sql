-- The audit table must add up: trips attributed to a first-matching rule = trips actually rejected.
with summary as (
    select sum(rows_excluded_first_match) as excluded_in_summary
    from {{ ref('dq_exclusion_summary') }}
),
actual as (
    select count(*) as rejected_rows
    from {{ ref('int_trips_dq_flagged') }}
    where is_valid = 0
)
select
    summary.excluded_in_summary,
    actual.rejected_rows
from summary, actual
where summary.excluded_in_summary <> actual.rejected_rows
